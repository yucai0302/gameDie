"""CS2 Game State Integration (GSI) HTTP 服务器。

CS2/CSGO 会根据 cfg 目录下的 ``gamestate_integration_*.cfg`` 配置文件，
定期向本地 HTTP 端点 POST 游戏状态 JSON。本模块启动一个轻量 HTTP
服务器接收这些数据，并通过状态变化检测比赛事件：

事件类型：
- match_start  : 新地图/比赛开始
- match_end    : 比赛结束（map phase = gameover）
- round_start  : 回合开始（freezetime）
- round_end    : 回合结束（over，含胜负、比分）
- kill         : 玩家击杀（match_stats.kills 递增）
- death        : 玩家死亡（match_stats.deaths 递增 或 health→0）

GSI 配置文件格式（写入 CS2 cfg 目录）::

    "DiePlay GSI"
    {
        "uri"      "http://localhost:3100"
        "timeout"  "0.1"
        "buffer"   "0.1"
        "throttle" "0.5"
        "heartbeat" "15.0"
        "auth" { "token" "dieplay-gsi-token" }
        "data"
        {
            "provider"      "1"
            "map"           "1"
            "round"         "1"
            "player_id"     "1"
            "player_state"  "1"
            "player_match_stats" "1"
        }
    }
"""
import json
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime
from typing import Callable, Dict, List, Optional

from config import GSI_AUTH_TOKEN, GSI_HOST, GSI_PORT

logger = logging.getLogger(__name__)

# GSI 配置文件名（必须以 gamestate_integration_ 开头，CS2 才会加载）
GSI_CONFIG_FILENAME = "gamestate_integration_dieplay.cfg"

# 死亡事件冷却时间（秒）：防止同一帧多次 POST 导致重复触发
_DEATH_COOLDOWN = 2.0


# CS2 武器原始名 → 友好显示名
_WEAPON_NAME_MAP: Dict[str, str] = {
    "weapon_ak47": "AK-47",
    "weapon_m4a1": "M4A1-S",
    "weapon_m4a1_silencer": "M4A1-S",
    "weapon_aug": "AUG",
    "weapon_sg556": "SG 553",
    "weapon_awp": "AWP",
    "weapon_ssg08": "SSG 08",
    "weapon_scar20": "SCAR-20",
    "weapon_g3sg1": "G3SG1",
    "weapon_galilar": "Galil AR",
    "weapon_famas": "FAMAS",
    "weapon_mp9": "MP9",
    "weapon_mac10": "MAC-10",
    "weapon_mp7": "MP7",
    "weapon_mp5sd": "MP5-SD",
    "weapon_ump45": "UMP-45",
    "weapon_p90": "P90",
    "weapon_bizon": "PP-Bizon",
    "weapon_nova": "Nova",
    "weapon_xm1014": "XM1014",
    "weapon_sawedoff": "Sawed-Off",
    "weapon_mag7": "MAG-7",
    "weapon_m249": "M249",
    "weapon_negev": "Negev",
    "weapon_glock": "Glock-18",
    "weapon_usp_silencer": "USP-S",
    "weapon_hkp2000": "P2000",
    "weapon_p250": "P250",
    "weapon_fiveseven": "Five-SeveN",
    "weapon_tec9": "Tec-9",
    "weapon_cz75a": "CZ75-Auto",
    "weapon_revolver": "R8 Revolver",
    "weapon_deagle": "Desert Eagle",
    "weapon_knife": "Knife",
    "weapon_knife_t": "Knife",
    "weapon_knife_ct": "Knife",
    "weapon_flashbang": "Flashbang",
    "weapon_hegrenade": "HE Grenade",
    "weapon_smokegrenade": "Smoke Grenade",
    "weapon_molotov": "Molotov",
    "weapon_incgrenade": "Incendiary",
    "weapon_decoy": "Decoy",
    "weapon_c4": "C4",
    "weapon_taser": "Zeus x27",
}


def _friendly_weapon_name(raw: str) -> str:
    """将 GSI 武器原始名（如 weapon_ak47）转为友好显示名（如 AK-47）。"""
    if not raw:
        return ""
    return _WEAPON_NAME_MAP.get(raw, raw.replace("weapon_", "").upper())


def _extract_weapon_info(player: Optional[Dict]) -> Dict:
    """从 GSI player.weapons 提取武器信息。

    Returns:
        {"active_weapon": 原始名, "active_weapon_name": 友好名,
         "weapons": [原始名列表], "weapon_names": [友好名列表]}
    """
    result: Dict = {
        "active_weapon": "",
        "active_weapon_name": "",
        "weapons": [],
        "weapon_names": [],
    }
    if not player or not isinstance(player, dict):
        return result
    weapons = player.get("weapons")
    if not weapons or not isinstance(weapons, dict):
        return result
    for _key, w in weapons.items():
        if not isinstance(w, dict):
            continue
        name = w.get("name", "")
        if not name:
            continue
        result["weapons"].append(name)
        result["weapon_names"].append(_friendly_weapon_name(name))
        if w.get("state") == "active":
            result["active_weapon"] = name
            result["active_weapon_name"] = _friendly_weapon_name(name)
    return result


class GSIState:
    """跟踪玩家游戏状态，检测并发出比赛事件。

    通过对比前后两帧 GSI payload 的差异来检测事件：
    - map.phase 变化 → match_start / match_end
    - round.phase 变化 → round_start / round_end
    - match_stats.kills 递增 → kill
    - match_stats.deaths 递增 或 health→0 → death
    - health 从 0 → >0 → respawn（复活/新回合开始）
    - steamid 变化 → 观战切换（重置跟踪，不触发事件）
    """

    def __init__(self):
        # 前一帧状态
        self._prev_deaths: Optional[int] = None
        self._prev_kills: Optional[int] = None
        self._prev_health: Optional[int] = None
        self._prev_steamid: Optional[str] = None
        self._prev_round_phase: Optional[str] = None
        self._prev_map_phase: Optional[str] = None
        self._prev_map_name: Optional[str] = None
        self._prev_round_number: Optional[int] = None
        self._last_death_ts: float = 0.0
        self._last_kill_ts: float = 0.0
        self._lock = threading.Lock()

        # 当前比赛信息（供日志/调试用）
        self.player_name: str = ""
        self.player_steamid: str = ""
        self.map_name: str = ""
        self.map_mode: str = ""
        self.round_number: int = 0

        # 事件回调列表
        self._event_callbacks: List[Callable[[Dict], None]] = []

    def add_callback(self, cb: Callable[[Dict], None]) -> None:
        """注册一个事件回调。"""
        self._event_callbacks.append(cb)

    def feed(self, payload: Dict) -> None:
        """处理一条 GSI payload，检测事件并调用回调。

        Args:
            payload: CS2 POST 过来的完整 JSON dict
        """
        player = payload.get("player")
        map_data = payload.get("map")
        round_data = payload.get("round")

        # 更新地图信息
        if map_data and isinstance(map_data, dict):
            self.map_name = map_data.get("name", "")
            self.map_mode = map_data.get("mode", "")
            round_num = map_data.get("round")
            if round_num is not None:
                try:
                    self.round_number = int(round_num)
                except (TypeError, ValueError):
                    pass

        # 更新玩家身份信息
        if player and isinstance(player, dict):
            name = player.get("name")
            steamid = player.get("steamid")
            if name:
                self.player_name = name
            if steamid:
                self.player_steamid = steamid

        events = self._detect_events(payload, player, map_data, round_data)

        for event in events:
            for cb in self._event_callbacks:
                try:
                    cb(event)
                except Exception as e:
                    logger.warning("GSI 事件回调异常: %s", e)

    def _detect_events(
        self,
        payload: Dict,
        player: Optional[Dict],
        map_data: Optional[Dict],
        round_data: Optional[Dict],
    ) -> List[Dict]:
        """检测所有事件，返回事件列表。"""
        events: List[Dict] = []
        now_iso = datetime.utcnow().isoformat() + "Z"

        with self._lock:
            # === 地图/比赛阶段变化 ===
            current_map_phase = None
            current_map_name = None
            if map_data:
                current_map_phase = map_data.get("phase", "")
                current_map_name = map_data.get("name", "")

            if current_map_phase and current_map_phase != self._prev_map_phase:
                if current_map_phase == "live" and self._prev_map_phase is None:
                    # 新比赛开始
                    events.append({
                        "event_type": "match_start",
                        "timestamp": now_iso,
                        "data": {
                            "map": current_map_name or "",
                            "mode": map_data.get("mode", "") if map_data else "",
                            "player": self.player_name,
                            "steamid": self.player_steamid,
                        },
                    })
                elif current_map_phase == "gameover":
                    # 比赛结束
                    score_ct = map_data.get("score_ct", 0) if map_data else 0
                    score_t = map_data.get("score_t", 0) if map_data else 0
                    events.append({
                        "event_type": "match_end",
                        "timestamp": now_iso,
                        "round_number": self.round_number,
                        "data": {
                            "map": current_map_name or "",
                            "score_ct": score_ct,
                            "score_t": score_t,
                            "rounds": self.round_number,
                        },
                    })

            # 地图名变化也算新比赛
            if (
                current_map_name
                and self._prev_map_name
                and current_map_name != self._prev_map_name
                and current_map_phase == "live"
            ):
                events.append({
                    "event_type": "match_start",
                    "timestamp": now_iso,
                    "data": {
                        "map": current_map_name,
                        "mode": map_data.get("mode", "") if map_data else "",
                        "player": self.player_name,
                        "steamid": self.player_steamid,
                    },
                })

            self._prev_map_phase = current_map_phase
            self._prev_map_name = current_map_name

            # === 回合阶段变化 ===
            current_round_phase = None
            if round_data:
                current_round_phase = round_data.get("phase", "")

            if current_round_phase and current_round_phase != self._prev_round_phase:
                if current_round_phase == "freezetime":
                    # 回合开始（购买冻结期）
                    money = None
                    equip_value = None
                    armor = None
                    helmet = None
                    weapon_info: Dict = {}
                    if player:
                        state = player.get("state") or {}
                        money = state.get("money")
                        equip_value = state.get("equipment_value")
                        armor = state.get("armor")
                        helmet = state.get("helmet")
                        weapon_info = _extract_weapon_info(player)
                    events.append({
                        "event_type": "round_start",
                        "timestamp": now_iso,
                        "round_number": self.round_number,
                        "data": {
                            "round": self.round_number,
                            "money": money,
                            "equipment_value": equip_value,
                            "armor": armor,
                            "helmet": helmet,
                            "weapons": weapon_info.get("weapons", []),
                            "weapon_names": weapon_info.get("weapon_names", []),
                            "active_weapon": weapon_info.get("active_weapon", ""),
                            "active_weapon_name": weapon_info.get("active_weapon_name", ""),
                            "map": self.map_name,
                        },
                    })
                elif current_round_phase == "over":
                    # 回合结束
                    win_team = round_data.get("win_team", "") if round_data else ""
                    score_ct = map_data.get("score_ct", 0) if map_data else 0
                    score_t = map_data.get("score_t", 0) if map_data else 0
                    bomb = round_data.get("bomb", "") if round_data else ""
                    events.append({
                        "event_type": "round_end",
                        "timestamp": now_iso,
                        "round_number": self.round_number,
                        "data": {
                            "round": self.round_number,
                            "win_team": win_team,
                            "score_ct": score_ct,
                            "score_t": score_t,
                            "bomb": bomb,
                        },
                    })

            self._prev_round_phase = current_round_phase

            # === 玩家状态变化 ===
            if not player:
                return events

            state = player.get("state") or {}
            match_stats = player.get("match_stats") or {}

            deaths = match_stats.get("deaths")
            kills = match_stats.get("kills")
            health = state.get("health")

            # === 关键防误报：steamid 变化时重置跟踪 ===
            steamid = player.get("steamid")
            if steamid != self._prev_steamid:
                logger.debug(
                    "steamid 变化: %s -> %s，重置跟踪状态",
                    self._prev_steamid, steamid,
                )
                self._prev_steamid = steamid
                self._prev_deaths = deaths if deaths is not None else None
                self._prev_kills = kills if kills is not None else None
                self._prev_health = health if health is not None else None
                return events

            # === 击杀事件：kills 计数器递增 ===
            if kills is not None and self._prev_kills is not None:
                try:
                    if int(kills) > int(self._prev_kills):
                        now_ts = datetime.utcnow().timestamp()
                        if now_ts - self._last_kill_ts > _DEATH_COOLDOWN:
                            self._last_kill_ts = now_ts
                            w_info = _extract_weapon_info(player)
                            events.append({
                                "event_type": "kill",
                                "timestamp": now_iso,
                                "round_number": self.round_number,
                                "data": {
                                    "round": self.round_number,
                                    "kills": kills,
                                    "weapon": w_info.get("active_weapon", ""),
                                    "weapon_name": w_info.get("active_weapon_name", ""),
                                    "round_kills": state.get("round_kills"),
                                    "round_killhs": state.get("round_killhs"),
                                    "map": self.map_name,
                                },
                            })
                except (TypeError, ValueError):
                    pass

            # === 死亡事件 ===
            died = False
            death_reason = ""

            # 主信号：match_stats.deaths 计数器递增
            if deaths is not None and self._prev_deaths is not None:
                try:
                    if int(deaths) > int(self._prev_deaths):
                        died = True
                        death_reason = "deaths_counter"
                except (TypeError, ValueError):
                    pass

            # 辅助信号：health 从 >0 变为 0
            if not died and health is not None and self._prev_health is not None:
                try:
                    if int(self._prev_health) > 0 and int(health) == 0:
                        died = True
                        death_reason = "health_zero"
                except (TypeError, ValueError):
                    pass

            # 冷却检查
            if died:
                now_ts = datetime.utcnow().timestamp()
                if (now_ts - self._last_death_ts) < _DEATH_COOLDOWN:
                    died = False
                else:
                    self._last_death_ts = now_ts

            if died:
                w_info = _extract_weapon_info(player)
                events.append({
                    "event_type": "death",
                    "timestamp": now_iso,
                    "round_number": self.round_number,
                    "data": {
                        "round": self.round_number,
                        "source": "gsi",
                        "reason": death_reason,
                        "player": self.player_name,
                        "steamid": self.player_steamid,
                        "deaths": deaths,
                        "health": health,
                        "active_weapon": w_info.get("active_weapon", ""),
                        "active_weapon_name": w_info.get("active_weapon_name", ""),
                        "round_kills": state.get("round_kills"),
                        "round_killhs": state.get("round_killhs"),
                        "armor": state.get("armor"),
                        "helmet": state.get("helmet"),
                        "map": self.map_name,
                    },
                })

            # === 复活事件：health 从 0 → >0（新回合开始/重生）===
            if (
                health is not None
                and self._prev_health is not None
                and not died  # 本帧不是刚死亡
            ):
                try:
                    if int(self._prev_health) == 0 and int(health) > 0:
                        events.append({
                            "event_type": "respawn",
                            "timestamp": now_iso,
                            "round_number": self.round_number,
                            "data": {
                                "round": self.round_number,
                                "health": health,
                                "map": self.map_name,
                            },
                        })
                except (TypeError, ValueError):
                    pass

            # 更新前一次状态
            if deaths is not None:
                self._prev_deaths = deaths
            if kills is not None:
                self._prev_kills = kills
            if health is not None:
                self._prev_health = health

        return events


# ---------------- HTTP 服务器 ----------------

# 全局状态实例（模块级单例，HTTP handler 通过闭包访问）
_state = GSIState()

# GSI 原始帧回调列表（用于性能采集：FPS/卡顿检测）
_gsi_payload_callbacks: List[Callable[[Dict], None]] = []


class _GSIRequestHandler(BaseHTTPRequestHandler):
    """处理 CS2 发来的 GSI POST 请求。"""

    # 关闭默认的 BaseHTTPRequestHandler 日志，避免刷屏
    def log_message(self, format, *args):  # noqa: A002
        pass

    def do_POST(self) -> None:  # noqa: N802
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            payload = json.loads(raw.decode("utf-8"))
        except Exception as e:
            logger.warning("解析 GSI POST body 失败: %s", e)
            self.send_response(400)
            self.end_headers()
            return

        # 校验 auth token（如果配置了的话）
        auth = payload.get("auth") or {}
        token = auth.get("token", "")
        if GSI_AUTH_TOKEN and token != GSI_AUTH_TOKEN:
            logger.debug("GSI auth token 不匹配，忽略 (got=%s)", token)
            self.send_response(401)
            self.end_headers()
            return

        # 处理状态
        _state.feed(payload)

        # 通知 GSI 帧回调（用于性能采集：FPS/卡顿检测）
        for cb in _gsi_payload_callbacks:
            try:
                cb(payload)
            except Exception:
                pass

        self.send_response(200)
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        """简单的健康检查端点。"""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        body = json.dumps({
            "service": "DiePlay GSI Server",
            "player": _state.player_name,
            "steamid": _state.player_steamid,
            "map": _state.map_name,
            "round": _state.round_number,
        }).encode("utf-8")
        self.wfile.write(body)


class GSIServer:
    """GSI HTTP 服务器包装：在后台线程中运行。"""

    def __init__(self, on_death: Callable[[Dict], None] = None, on_event: Callable[[Dict], None] = None, on_gsi_payload: Callable[[Dict], None] = None):
        self.host = GSI_HOST
        self.port = GSI_PORT
        self._httpd: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None

        # GSI 原始帧回调（用于性能采集：FPS/卡顿检测）
        self._on_gsi_payload = on_gsi_payload
        if on_gsi_payload is not None:
            _gsi_payload_callbacks.append(on_gsi_payload)

        # 注册回调
        if on_death is not None:
            # 兼容旧接口：on_death 只接收 death 事件
            _state.add_callback(self._make_death_filter(on_death))
        if on_event is not None:
            _state.add_callback(on_event)

    @staticmethod
    def _make_death_filter(on_death: Callable[[Dict], None]) -> Callable[[Dict], None]:
        """过滤出 death 事件，转换格式后调用 on_death。"""
        def _filter(event: Dict) -> None:
            if event.get("event_type") == "death":
                # 转换为旧格式 {"game", "timestamp", "metadata"}
                old_format = {
                    "game": "csgo",
                    "timestamp": event["timestamp"],
                    "metadata": event.get("data", {}),
                }
                on_death(old_format)
        return _filter

    def start(self) -> bool:
        """启动 HTTP 服务器。返回是否成功。"""
        try:
            self._httpd = ThreadingHTTPServer((self.host, self.port), _GSIRequestHandler)
        except OSError as e:
            logger.warning("GSI 服务器绑定 %s:%s 失败: %s", self.host, self.port, e)
            return False
        self._thread = threading.Thread(
            target=self._httpd.serve_forever, daemon=True, name="gsi-http-server"
        )
        self._thread.start()
        logger.info("GSI 服务器已启动 → http://%s:%s", self.host, self.port)
        return True

    def stop(self) -> None:
        if self._httpd:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None
        logger.info("GSI 服务器已停止")

    @property
    def is_running(self) -> bool:
        return self._httpd is not None and self._thread is not None and self._thread.is_alive()


# ---------------- CS2 cfg 目录定位 + 配置文件写入 ----------------

def find_cs2_cfg_dir(exe_path: str) -> Optional[str]:
    """从 CS2 进程的 exe 路径推导 cfg 目录。

    CS2 exe 典型路径：
        <install>\\game\\bin\\win64\\cs2.exe
    对应 cfg 目录：
        <install>\\game\\csgo\\cfg

    Args:
        exe_path: cs2.exe / csgo.exe 的完整路径

    Returns:
        cfg 目录的绝对路径，找不到返回 None
    """
    if not exe_path:
        return None

    exe_path = exe_path.replace("/", "\\")
    parts = exe_path.split("\\")

    # 向上查找 "game" 目录，然后取 game\\csgo\\cfg
    for i in range(len(parts) - 1, -1, -1):
        if parts[i].lower() == "game":
            game_dir = "\\".join(parts[: i + 1])
            cfg_dir = os.path.join(game_dir, "csgo", "cfg")
            if os.path.isdir(cfg_dir):
                return cfg_dir
            # CS:GO 老版本目录结构：csgo\\cfg 直接在安装目录下
            cfg_dir_alt = os.path.join(game_dir, "cfg")
            if os.path.isdir(cfg_dir_alt):
                return cfg_dir_alt

    # 兜底：exe 同级或上级的 csgo\\cfg
    exe_dir = os.path.dirname(exe_path)
    candidates = [
        os.path.join(exe_dir, "..", "..", "csgo", "cfg"),
        os.path.join(exe_dir, "..", "csgo", "cfg"),
        os.path.join(exe_dir, "cfg"),
    ]
    for c in candidates:
        c = os.path.normpath(c)
        if os.path.isdir(c):
            return c

    return None


def write_gsi_config(cfg_dir: str, host: str = GSI_HOST, port: int = GSI_PORT, token: str = GSI_AUTH_TOKEN) -> str:
    """将 GSI 配置文件写入 CS2 cfg 目录。

    Args:
        cfg_dir: CS2 的 cfg 目录绝对路径
        host: GSI 服务器监听地址
        port: GSI 服务器监听端口
        token: auth token

    Returns:
        写入的配置文件完整路径
    """
    uri = f"http://{host}:{port}"
    # 注意：GSI cfg 文件使用 VDF 格式（类似 KeyValues），不是 JSON
    content = (
        '"DiePlay GSI"\n'
        '{\n'
        f'    "uri"      "{uri}"\n'
        '    "timeout"  "0.1"\n'
        '    "buffer"   "0.1"\n'
        '    "throttle" "0.5"\n'
        '    "heartbeat" "15.0"\n'
        '    "auth"\n'
        '    {\n'
        f'        "token" "{token}"\n'
        '    }\n'
        '    "data"\n'
        '    {\n'
        '        "provider"      "1"\n'
        '        "map"           "1"\n'
        '        "round"         "1"\n'
        '        "player_id"     "1"\n'
        '        "player_state"  "1"\n'
        '        "player_weapons" "1"\n'
        '        "player_match_stats" "1"\n'
        '    }\n'
        '}\n'
    )
    cfg_path = os.path.join(cfg_dir, GSI_CONFIG_FILENAME)
    try:
        with open(cfg_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info("GSI 配置文件已写入: %s", cfg_path)
    except Exception as e:
        logger.warning("写入 GSI 配置文件失败: %s", e)
    return cfg_path


def setup_gsi(
    exe_path: str,
    on_death: Callable[[Dict], None] = None,
    on_event: Callable[[Dict], None] = None,
    on_gsi_payload: Callable[[Dict], None] = None,
) -> Optional[GSIServer]:
    """一键完成 GSI 设置：定位 cfg 目录 → 写配置文件 → 启动 HTTP 服务器。

    Args:
        exe_path: CS2/CSGO 进程的 exe 路径
        on_death: 死亡事件回调（兼容旧接口）
        on_event: 通用事件回调（所有事件类型）
        on_gsi_payload: GSI 原始帧回调（用于性能采集）

    Returns:
        启动成功的 GSIServer 实例，失败返回 None
    """
    cfg_dir = find_cs2_cfg_dir(exe_path)
    if not cfg_dir:
        logger.warning(
            "无法从 exe 路径定位 CS2 cfg 目录: %s。"
            "GSI 死亡检测将无法工作。", exe_path,
        )
        return None

    logger.info("CS2 cfg 目录: %s", cfg_dir)
    write_gsi_config(cfg_dir)

    server = GSIServer(on_death=on_death, on_event=on_event, on_gsi_payload=on_gsi_payload)
    if not server.start():
        return None
    return server
