"""Agent 入口（主循环）。

主循环逻辑：
1. 启动 BackendClient，拉取配置
2. 进入主循环（while True），每 POLLING_INTERVAL 秒：
   - 检测进程
   - 当前无 adapter 但检测到游戏运行 → 创建对应 adapter 并 start
   - adapter 不 alive（游戏关闭）→ stop adapter
   - 游戏切换时处理观看会话清理
3. 每 HEARTBEAT_INTERVAL 秒上报一次 games_status
4. 适配器 on_death 回调：
   - 调用 reporter.report_death → 拿到 watch_session_id
   - 调用 browser.open_browser(redirect_url)
   - 记录观看会话
5. 优雅退出：捕获 Ctrl+C，stop adapter，end_watch_session，sys.exit
6. 日志：logging 同时输出到 console 和 agent/logs/agent.log
"""
import os
import sys
import time
import logging
import importlib
import threading
from typing import Dict, Optional

# 确保 agent 目录在 sys.path 上（用绝对 import）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from reporter import BackendClient
from detector import list_game_processes
from window_manager import minimize_game_and_open_browser, focus_window_by_pid
import browser

logger = logging.getLogger("agent")


def setup_logging() -> None:
    """配置日志：同时输出到 console 和 agent/logs/agent.log。"""
    os.makedirs(config.AGENT_LOG_DIR, exist_ok=True)
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(
                os.path.join(config.AGENT_LOG_DIR, "agent.log"), encoding="utf-8"
            ),
        ],
    )


def load_adapter_class(class_path: str):
    """动态加载适配器类。class_path 形如 'adapters.csgo.CSGOAdapter'。"""
    module_path, cls_name = class_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, cls_name)


class Agent:
    """Agent 主控对象。"""

    def __init__(self):
        self.client = BackendClient()
        self.cfg: Dict = {}
        self.current_adapter = None
        # 当前正在运行的游戏信息 {"game_id":..., "pid":..., "exe_path":...}
        self.current_game: Optional[Dict] = None
        self.last_heartbeat = 0.0
        # 当前比赛 ID（由后端分配）
        self.current_match_id: Optional[str] = None
        # 性能采集器
        from perf_collector import PerfCollector
        self.perf_collector = PerfCollector()
        # 性能上报计数器（每 N 次心跳上报一次）
        self._perf_tick = 0
        # 自动返回游戏：待返回状态 + 兜底定时器
        self._pending_return_pid: Optional[int] = None
        self._return_timer: Optional[threading.Timer] = None
        # 死亡事件防重入时间戳
        self._last_death_ts: float = 0.0
        # 自动录屏控制器（可插拔：初始化失败或整个模块删除都不影响现有功能）
        try:
            from recording import RecordingController
            self.recorder = RecordingController(
                client=self.client,
                get_match_id=lambda: self.current_match_id,
                get_game_pid=lambda: (self.current_game or {}).get("pid"),
            )
        except Exception as e:
            logger.warning("录屏模块初始化失败，已跳过: %s", e)
            self.recorder = None

    # ---- 死亡回调 ----
    def on_death(self, event: Dict) -> None:
        """适配器死亡事件回调。

        流程：
        1. 上报死亡事件，拿 watch_session_id
        2. 最小化游戏窗口，打开用户配置的视频页（redirect_url）
        3. 若开启自动返回：启动后台倒计时，到点自动把游戏窗口拉回前台
        """
        # 全局防重入：同一死亡事件可能被 GSI 和日志各检测一次，
        # 5 秒内的重复 on_death 调用直接忽略
        now_ts = time.time()
        if now_ts - self._last_death_ts < 5.0:
            logger.info("忽略重复死亡事件（距上次 %.1fs < 5s 冷却）", now_ts - self._last_death_ts)
            return
        self._last_death_ts = now_ts

        logger.info(
            "检测到死亡事件: game=%s metadata=%s",
            event.get("game"),
            event.get("metadata"),
        )
        result = self.client.report_death(
            game=event.get("game", ""),
            timestamp=event.get("timestamp", ""),
            metadata=event.get("metadata", {}),
        )
        watch_session_id = result.get("watch_session_id", "")
        redirect_url = self.cfg.get("redirect_url") or config.DEFAULT_REDIRECT_URL

        game_pid = self.current_game.get("pid") if self.current_game else None

        # 最小化游戏 + 打开视频页（保持原有行为不变）
        if watch_session_id:
            if game_pid:
                minimize_game_and_open_browser(
                    game_pid,
                    lambda url: browser.start_watch_session(watch_session_id, url),
                    redirect_url,
                )
            else:
                browser.start_watch_session(watch_session_id, redirect_url)
        else:
            logger.warning("未拿到 watch_session_id，仅打开浏览器")
            if game_pid:
                minimize_game_and_open_browser(game_pid, browser.open_browser, redirect_url)
            else:
                browser.open_browser(redirect_url)

        # 自动返回游戏：记录待返回状态 + 启动兜底定时器
        overlay_cfg = self.cfg.get("overlay") or {}
        if overlay_cfg.get("auto_return_enabled") and game_pid:
            self._pending_return_pid = game_pid
            on_respawn = overlay_cfg.get("auto_return_on_respawn", True)
            delay = int(overlay_cfg.get("auto_return_seconds", 30))
            if on_respawn:
                # 事件驱动模式：兜底定时器（若 N 秒内未检测到复活则强制返回）
                logger.info(
                    "自动返回已启用（复活驱动），兜底超时 %ss，pid=%s",
                    delay, game_pid,
                )
            else:
                # 纯定时器模式
                logger.info(
                    "自动返回已启用（纯定时器），%ss 后返回，pid=%s",
                    delay, game_pid,
                )
            # 取消旧的定时器（若有）
            if self._return_timer:
                self._return_timer.cancel()
            t = threading.Timer(delay, self._auto_return_to_game, args=(game_pid,))
            t.daemon = True
            self._return_timer = t
            t.start()

    def _auto_return_to_game(self, pid: int) -> None:
        """兜底定时器到期：将游戏窗口拉回前台。"""
        self._do_return(pid, source="timer_fallback")

    def _trigger_return_now(self, pid: int, source: str = "respawn") -> None:
        """事件驱动：检测到复活/新回合时立即返回游戏，取消兜底定时器。"""
        if self._return_timer:
            self._return_timer.cancel()
            self._return_timer = None
        self._do_return(pid, source=source)

    def _do_return(self, pid: int, source: str) -> None:
        """实际执行返回游戏操作。"""
        # 清除待返回状态（防止重复触发）
        if self._pending_return_pid == pid:
            self._pending_return_pid = None
        self._return_timer = None
        try:
            ok = focus_window_by_pid(pid)
            if ok:
                logger.info("自动返回游戏成功 [%s] pid=%s", source, pid)
            else:
                logger.warning("自动返回游戏失败 [%s]：未找到游戏窗口 pid=%s", source, pid)
        except Exception as e:
            logger.warning("自动返回游戏异常 [%s]: %s", source, e)

    # ---- GSI 帧回调（性能采集） ----
    def on_gsi_payload(self, payload: Dict) -> None:
        """每次收到 GSI 数据帧时调用，喂给性能采集器计算 FPS/卡顿。"""
        try:
            self.perf_collector.feed_gsi(payload)
        except Exception:
            pass

    # ---- 比赛事件回调 ----
    def on_match_event(self, event: Dict) -> None:
        """GSI 比赛事件回调：回合、击杀、比赛开始/结束、复活等。"""
        # 录屏控制器：一行注入，接收所有事件（match_start/death/kill/respawn/match_end）
        if self.recorder:
            self.recorder.on_event(event)

        event_type = event.get("event_type", "")
        timestamp = event.get("timestamp", "")
        round_number = event.get("round_number")
        data = event.get("data", {})

        logger.info(
            "比赛事件: type=%s round=%s data=%s",
            event_type, round_number, data,
        )

        # === 事件驱动自动返回：检测到复活/新回合 → 立即拉回游戏窗口 ===
        if event_type in ("respawn", "round_start") and self._pending_return_pid:
            overlay_cfg = self.cfg.get("overlay") or {}
            if (
                overlay_cfg.get("auto_return_enabled")
                and overlay_cfg.get("auto_return_on_respawn", True)
            ):
                pid = self._pending_return_pid
                logger.info(
                    "检测到 %s 事件，触发事件驱动自动返回 (pid=%s)",
                    event_type, pid,
                )
                self._trigger_return_now(pid, source=event_type)

        if event_type == "match_start":
            # 新比赛开始 → 向后端创建比赛
            result = self.client.report_match_start(
                map_name=data.get("map", ""),
                mode=data.get("mode", ""),
                player_name=data.get("player", ""),
                player_steamid=data.get("steamid", ""),
            )
            self.current_match_id = result.get("match_id")
            logger.info("新比赛已创建: match_id=%s", self.current_match_id)
            return

        if event_type == "match_end":
            # 比赛结束 → 向后端结束比赛
            if self.current_match_id:
                self.client.report_match_end(
                    self.current_match_id,
                    score_ct=data.get("score_ct", 0),
                    score_t=data.get("score_t", 0),
                    rounds_played=data.get("rounds", 0),
                )
                logger.info("比赛已结束: match_id=%s", self.current_match_id)
                self.current_match_id = None
            return

        # 其他事件（round_start, round_end, kill, death）→ 上报到后端
        if self.current_match_id:
            self.client.report_match_event(
                match_id=self.current_match_id,
                event_type=event_type,
                timestamp=timestamp,
                round_number=round_number,
                data=data,
            )

    # ---- 适配器生命周期 ----
    def _start_adapter(self, game_info: Dict) -> None:
        game_id = game_info["game_id"]
        game_cfg = config.GAME_REGISTRY.get(game_id)
        if not game_cfg:
            logger.warning("未注册的游戏: %s", game_id)
            return
        try:
            cls = load_adapter_class(game_cfg["adapter_class"])
        except Exception as e:
            logger.warning("加载适配器失败 %s: %s", game_cfg["adapter_class"], e)
            return
        adapter = cls(
            exe_path=game_info.get("exe_path", ""),
            on_death=self.on_death,
            on_event=self.on_match_event,
            on_gsi_payload=self.on_gsi_payload,
        )
        try:
            adapter.start()
        except Exception as e:
            logger.warning("启动适配器异常 %s: %s", game_cfg["name"], e)
        self.current_adapter = adapter
        self.current_game = game_info
        logger.info(
            "已启动 %s 适配器 (pid=%s)", game_cfg["name"], game_info.get("pid")
        )

    def _stop_adapter(self) -> None:
        if self.current_adapter:
            logger.info("停止适配器 %s", self.current_adapter.__class__.__name__)
            try:
                self.current_adapter.stop()
            except Exception as e:
                logger.warning("停止适配器异常: %s", e)
            self.current_adapter = None
            self.current_game = None

        # 录屏收尾：游戏退出时尽量完成在途片段的上传（可插拔，失败不影响后续）
        if self.recorder:
            try:
                self.recorder.shutdown()
            except Exception as e:
                logger.warning("录屏收尾异常: %s", e)

        # 游戏退出时结束当前比赛
        if self.current_match_id:
            logger.info("游戏退出，结束比赛: %s", self.current_match_id)
            self.client.report_match_end(self.current_match_id)
            self.current_match_id = None

    # ---- 心跳 ----
    def _heartbeat(self, games) -> None:
        current = self.current_game["game_id"] if self.current_game else None
        current_pid = self.current_game.get("pid") if self.current_game else None
        # 上报所有已注册游戏及其运行状态（与后端 GameInfo 字段对齐）
        running_ids = {g["game_id"] for g in games}
        games_summary = []
        for game_id, info in config.GAME_REGISTRY.items():
            games_summary.append(
                {
                    "id": game_id,
                    "name": info["name"],
                    "process_names": info["process_names"],
                    "running": game_id in running_ids,
                }
            )
        self.client.report_games_status(
            games=games_summary,
            current_game=current,
            current_game_pid=current_pid,
        )

        # 刷新配置（每 6 次心跳约 30s 拉取一次，让 Overlay 等设置实时生效）
        self._cfg_tick = getattr(self, "_cfg_tick", 0) + 1
        if self._cfg_tick % 6 == 0:
            try:
                fresh = self.client.get_config()
                if fresh:
                    self.cfg = fresh
            except Exception:
                pass

        # 上报系统音量
        try:
            from volume_reader import get_volume
            vol = get_volume()
            if vol >= 0:
                self.client.report_volume(vol)
        except Exception:
            pass

        # 上报性能指标（每 2 次心跳上报一次 = 10 秒）
        self._perf_tick += 1
        if self._perf_tick % 2 == 0:
            try:
                game_pid = self.current_game.get("pid") if self.current_game else None
                metrics = self.perf_collector.collect(game_pid=game_pid)

                # 构建 latency 的 detail（包含加速器状态和服务器 IP）
                latency_detail = {}
                if metrics.get("accelerator"):
                    latency_detail["accelerator"] = metrics["accelerator"]
                if metrics.get("server_ip"):
                    latency_detail["server_ip"] = metrics["server_ip"]

                if metrics.get("latency") is not None:
                    self.client.report_perf("latency", metrics["latency"], detail=latency_detail)
                if metrics.get("fps") is not None:
                    self.client.report_perf("fps", metrics["fps"])
                if metrics.get("stutter") is not None:
                    self.client.report_perf("stutter", metrics["stutter"])
            except Exception as e:
                logger.debug("性能指标上报失败: %s", e)

    # ---- 主循环 ----
    def _tick(self) -> None:
        games = list_game_processes()
        running_game = games[0] if games else None

        if running_game is None:
            # 没有游戏运行
            if self.current_adapter is not None:
                logger.info("游戏已退出，停止适配器")
                self._stop_adapter()
                # 游戏退出时也清理观看会话并上报
                try:
                    browser.end_watch_session(self.client)
                except Exception:
                    pass
        else:
            if self.current_adapter is None:
                # 启动新适配器
                self._start_adapter(running_game)
            else:
                # 游戏切换
                if (
                    self.current_game
                    and self.current_game["game_id"] != running_game["game_id"]
                ):
                    logger.info(
                        "游戏切换: %s -> %s",
                        self.current_game["game_id"],
                        running_game["game_id"],
                    )
                    self._stop_adapter()
                    self._start_adapter(running_game)
                else:
                    # 同一游戏，检查适配器是否还活着
                    if not self.current_adapter.is_alive():
                        logger.info("适配器不再存活，重启")
                        self._stop_adapter()
                        self._start_adapter(running_game)

        # 心跳上报
        now = time.time()
        if now - self.last_heartbeat >= config.HEARTBEAT_INTERVAL:
            self._heartbeat(games)
            self.last_heartbeat = now

    def run(self) -> None:
        logger.info(
            "Agent 启动，后端=%s 轮询间隔=%ss",
            config.BACKEND_URL,
            config.POLLING_INTERVAL,
        )
        # 拉取配置
        try:
            self.cfg = self.client.get_config()
        except Exception as e:
            logger.warning("拉取配置失败: %s", e)
            self.cfg = {}
        if not self.cfg:
            self.cfg = {"redirect_url": config.DEFAULT_REDIRECT_URL}
        # 允许后端覆盖轮询/心跳间隔
        agent_cfg = self.cfg.get("agent") or {}
        if agent_cfg.get("polling_interval"):
            config.POLLING_INTERVAL = float(agent_cfg["polling_interval"])

        try:
            while True:
                self._tick()
                time.sleep(config.POLLING_INTERVAL)
        except KeyboardInterrupt:
            logger.info("收到退出信号，正在清理...")
        finally:
            self._stop_adapter()
            try:
                browser.end_watch_session(self.client)
            except Exception as e:
                logger.warning("结束观看会话异常: %s", e)
            sys.exit(0)


def main() -> None:
    setup_logging()
    agent = Agent()
    agent.run()


if __name__ == "__main__":
    main()
