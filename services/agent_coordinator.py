"""

Agent Coordinator



Coordinates Google ADK agents and manages their sessions.

"""



import os

import logging

import uuid
from pathlib import Path

from typing import Dict, Any, Optional, List

from datetime import datetime

import asyncio



from google.adk.runners import Runner

from google.adk.sessions import InMemorySessionService

from google.genai import types



from .config import agent_config, billing_flags

from .data_processor import DataProcessor
from .session_manager import SessionManager

from .message_handler import MessageHandler

from .photon_billing import get_billing_service

from .pricing_service import PricingService



logger = logging.getLogger(__name__)



# 会话管理配置

MAX_CONTEXT_MESSAGES = 16  # 最多保息6条消息（8轮对话），降低限制避免超息

CONTEXT_SUMMARY_THRESHOLD = 10  # 超过10条消息时提前警告

CONTEXT_AUTO_CLEAR_THRESHOLD = 12  # 超过12条消息时自动清理息息



# 🆕 工具名称到功能类型的映射（用于按功能扣费息

TOOL_FEATURE_MAPPING = {

    # 数据库查询工具（1 光子/次）

    'materials_project_query_tool': 'database',     # 1 光子

    'get_oqmd_phases': 'database',                  # 1 光子

    'search_cod_by_formula': 'database',            # 1 光子

    'get_aflow_data': 'database',                   # 1 光子

    'batch_database_search': 'database',            # 1 光子（批量查询按单次计费息

    'get_structure_recommendations': 'database',    # 1 光子



    # 文献搜索工具息 光子/次）

    'search_papers': 'search',                      # 1 光子

    # 结构生成与弛息

    'generate_crystal_structure': 'structure_gen',  # 10 光子

    'relax_structure': 'relaxation',                # 5 光子



    # 声子谱与热导率计息

    'calculate_phonon': 'phonon',                   # 5 光子

    'calculate_phonon_from_directory': 'batch_phonon', # 4 光子（批量优惠）

    'calculate_kappa': 'kappa',                     # 5 光子

    'calculate_kappa_from_cif': 'kappa',            # 5 光子

    'calculate_kappa_from_directory': 'batch_kappa', # 4 光子（批量优惠）

    'batch_calculate_kappa': 'batch_kappa',         # 4 光子（批量优惠）



    # 文献报告生成

    'generate_research_report': 'report',           # 30 光子

    'generate_research_report_with_data_collection': 'report',  # 30 光子



    # 文献分析

    'analyze_paper_content': 'analysis',            # 15 光子

    'batch_paper_analysis': 'analysis',             # 15 光子



    # 免费工具（不在映射中的工具默认免费）

    # 'get_paper_info': 0,                          # 获取论文信息（免费）

    # 'get_paper_content': 0,                       # 获取论文内容（免费）

    # 'download_paper': 0,                          # 下载论文（免费）

    # 'save_papers_to_csv': 0,                      # 保存到CSV（免费）

    # 'ingest_papers_to_vector_store': 0,           # 向量化存储（免费息

    # 'semantic_search_papers': 0,                  # 语义搜索（免费）

    # 'generate_research_plan': 0,                  # 生成研究计划（免费）

    # 'extract_and_validate_cif': 0,                # CIF验证（免费）

    # 'calculate_energy_from_cif': 0,               # 能量计算（免费）

    # 'health_check': 0,                            # 健康检查（免费息

}





class AgentCoordinator:

    """Coordinate Google ADK agents"""

    _LONG_RUNNING_TOOLS = {
        "batch_paper_analysis",
        "generate_research_report",
    }
    _SESSION_ID_EXEMPT_TOOLS = {
        "generate_research_plan",
    }



    def __init__(self, agents: Dict[str, Any]):

        """

        Initialize agent coordinator



        Args:

            agents: Dict of agent_id -> agent instance

        """

        self.agents = agents

        self.session_services: Dict[str, InMemorySessionService] = {}

        self.runners: Dict[str, Runner] = {}

        self.adk_sessions: Dict[str, Any] = {}
        self.session_id_map: Dict[str, str] = {}  # session_key -> session_id

        self.session_message_counts: Dict[str, int] = {}  # 跟踪每个会话的消息数息

        self.current_tool_calls: Dict[str, List[Dict[str, Any]]] = {}  # 跟踪当前消息的工具调息
        self.last_tool_call: Dict[str, Dict[str, Any]] = {}  # 跟踪每个会话最近一次工具调用

        self.message_billing_data: Dict[str, Dict[str, Any]] = {}  # 跟踪每条消息的计费数息(session_key -> billing_data)

        self.message_start_billing: Dict[str, Dict[str, Any]] = {}  # 记录消息开始时的计费状态

        self.stop_flags: Dict[str, bool] = {}  # 🆕 停止标志 (session_key -> should_stop)

        # 🆕 活跃任务登记（用于强制取消）

        self.active_tasks: Dict[str, asyncio.Task] = {}

        self.active_task_meta: Dict[str, Any] = {}
        self.heartbeat_tasks: Dict[str, asyncio.Task] = {}



    def _get_long_running_timeout(self, session_key: str, base_timeout: float) -> float:
        last_call = self.last_tool_call.get(session_key)
        if not last_call or last_call.get("status") != "pending":
            return base_timeout
        if last_call.get("name") in self._LONG_RUNNING_TOOLS:
            return max(base_timeout, 3600.0)
        return base_timeout

    def _start_task_heartbeat(
        self,
        session_key: str,
        websocket: Any,
        agent_id: str,
        session_id: Optional[str],
        interval: float = 20.0
    ) -> None:
        if session_key in self.heartbeat_tasks:
            task = self.heartbeat_tasks.get(session_key)
            if task and not task.done():
                return

        async def _beat() -> None:
            try:
                while True:
                    await asyncio.sleep(interval)
                    if self.should_stop(session_key):
                        break
                    if getattr(websocket, 'closed', False):
                        break
                    await MessageHandler.send_message(websocket, 'status', {
                        'status': 'working',
                        'message': 'Task is still running...',
                        'agentId': agent_id,
                        'sessionId': session_id,
                    })
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.warning(f'Heartbeat send failed: {e}')
            finally:
                self.heartbeat_tasks.pop(session_key, None)

        self.heartbeat_tasks[session_key] = asyncio.create_task(_beat())

    def _stop_task_heartbeat(self, session_key: str) -> None:
        task = self.heartbeat_tasks.get(session_key)
        if task and not task.done():
            task.cancel()
        self.heartbeat_tasks.pop(session_key, None)

    def _get_session_id_for_key(self, session_key: str) -> Optional[str]:
        session_id = self.session_id_map.get(session_key)
        if session_id:
            return session_id

        session = self.adk_sessions.get(session_key)
        if session:
            state = getattr(session, "state", None)
            if isinstance(state, dict):
                state_session_id = state.get("session_id")
                if state_session_id:
                    self.session_id_map[session_key] = state_session_id
                    return state_session_id

        return None

    def _persist_history_for_session_key(self, session_key: str, reason: str = "") -> None:
        session = self.adk_sessions.get(session_key)
        if not session:
            return

        session_events = getattr(session, "events", None) or []
        if not session_events:
            return

        try:
            from .hybrid_session_manager import HybridSessionManager

            session_id = self._get_session_id_for_key(session_key)
            stable_key = session_id or "default"
            HybridSessionManager.save_history(stable_key, session_events)

            suffix = f" reason={reason}" if reason else ""
            logger.info(f"💾 Saved {len(session_events)} events for {stable_key} ({session_key}){suffix}")
        except Exception as e:
            logger.warning(f"Failed to persist history for {session_key}: {e}")

    def _restore_history_from_disk(self, history_key: str) -> List[types.Content]:

        """Restore session history from disk (uses Redis when available)"""

        from .hybrid_session_manager import HybridSessionManager

        history_dicts = HybridSessionManager.load_history(history_key)

        

        if not history_dicts:

            return []



        restored_history = []

        try:

            for msg_data in history_dicts:

                parts = []

                for part_data in msg_data.get('parts', []):

                    if 'text' in part_data:

                        parts.append(types.Part(text=part_data['text']))

                

                if parts:

                    content = types.Content(role=msg_data.get('role'), parts=parts)

                    restored_history.append(content)

        except Exception as e:

            logger.error(f"息Failed to restore history for {history_key}: {e}")

            return []

            

        return restored_history

    def _persist_history_snapshot(self, session_id: Optional[str], session: Any) -> None:
        if not session_id:
            return
        try:
            from .hybrid_session_manager import HybridSessionManager

            session_events = getattr(session, 'events', None) or []
            if session_events:
                HybridSessionManager.save_history(session_id, session_events)
        except Exception as e:
            logger.warning(f"Failed to persist history snapshot for {session_id}: {e}")

    def _extract_event_text(self, event: Any, max_len: int = 200) -> Dict[str, Any]:
        parts = []
        for part in getattr(event, 'parts', []) or []:
            text = getattr(part, 'text', None)
            if text:
                parts.append(text)
        combined = " ".join(parts).strip()
        if max_len and len(combined) > max_len:
            combined = combined[:max_len] + "..."
        return {
            "role": getattr(event, 'role', None),
            "text": combined
        }

    def _normalize_tool_result_payload(self, result_data: Any) -> Any:
        """Best-effort normalization for tool outputs (AgentTool/MCP)."""
        if result_data is None:
            return result_data

        # If payload is already a dict, keep it as-is
        if isinstance(result_data, dict):
            # Some tool results nest JSON in a top-level content list
            content = result_data.get("content")
            if isinstance(content, list):
                parsed = self._extract_json_from_parts(content)
                if isinstance(parsed, dict):
                    return parsed
            return result_data

        # Try to parse JSON from plain string
        if isinstance(result_data, str):
            parsed = self._safe_json_load(result_data)
            return parsed if parsed is not None else result_data

        # Try to parse JSON from content parts list
        if isinstance(result_data, list):
            parsed = self._extract_json_from_parts(result_data)
            return parsed if parsed is not None else result_data

        return result_data

    def _unwrap_result_payload(self, result_data: Any) -> Any:
        """Unwrap nested result payloads like {"result": {...}}."""
        max_depth = 5
        depth = 0

        while isinstance(result_data, dict) and list(result_data.keys()) == ["result"] and depth < max_depth:
            depth += 1
            candidate = result_data.get("result")

            # Direct dict payload
            if isinstance(candidate, dict):
                result_data = candidate
                continue

            # List payload (pick first dict-like item)
            if isinstance(candidate, list):
                parsed = self._extract_json_from_parts(candidate)
                if isinstance(parsed, dict):
                    result_data = parsed
                    continue
                first_dict = next((item for item in candidate if isinstance(item, dict)), None)
                if first_dict is not None:
                    result_data = first_dict
                    continue
                break

            # String payload (attempt JSON)
            if isinstance(candidate, str):
                parsed = self._safe_json_load(candidate)
                if isinstance(parsed, dict):
                    result_data = parsed
                    continue
                break

            # MCP CallToolResult-like objects
            if hasattr(candidate, "structuredContent"):
                structured = getattr(candidate, "structuredContent")
                if isinstance(structured, dict):
                    result_data = structured
                    continue

            if hasattr(candidate, "content"):
                content = getattr(candidate, "content")
                parsed = self._extract_json_from_parts(content) if isinstance(content, list) else None
                if isinstance(parsed, dict):
                    result_data = parsed
                    continue

            break

        return result_data

    def _extract_json_from_parts(self, parts: List[Any]) -> Optional[Dict[str, Any]]:
        for item in parts:
            if item is None:
                continue
            text = getattr(item, "text", None)
            if text is None and isinstance(item, dict):
                text = item.get("text")
            if not text or not isinstance(text, str):
                continue
            parsed = self._safe_json_load(text)
            if isinstance(parsed, dict):
                return parsed
        return None

    def _safe_json_load(self, raw: str) -> Optional[Dict[str, Any]]:
        import json
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None

    def _looks_like_tool_payload(self, data: Dict[str, Any]) -> bool:
        if not data:
            return False
        keys = {
            "csv_file_path",
            "csv_download_url",
            "md_download_url",
            "summary_file_path",
            "report_file_path",
            "structures",
            "frontend_structures",
            "database_structures",
            "generated_structures",
            "images",
            "results_file",
            "batch_results_file",
            "phonon_dispersion_csv",
            "phonon_dos_csv",
            "cif_file_path",
            "cif_paths",
            "generated_files",
        }
        return any(key in data for key in keys)

    def _collect_tool_payloads(self, data: Any, max_depth: int = 4) -> List[Dict[str, Any]]:
        payloads: List[Dict[str, Any]] = []
        seen: set[int] = set()

        def visit(value: Any, depth: int) -> None:
            if depth > max_depth:
                return
            if isinstance(value, dict):
                is_wrapper = False
                if "results" in value and isinstance(value.get("results"), list):
                    wrapper_keys = {
                        "status",
                        "success",
                        "total",
                        "completed",
                        "failed",
                        "results",
                        "images",
                        "message",
                        "error",
                        "timestamp",
                    }
                    if set(value.keys()).issubset(wrapper_keys):
                        is_wrapper = True

                if self._looks_like_tool_payload(value) and not is_wrapper:
                    value_id = id(value)
                    if value_id not in seen:
                        seen.add(value_id)
                        payloads.append(value)
                for item in value.values():
                    visit(item, depth + 1)
            elif isinstance(value, list):
                for item in value:
                    visit(item, depth + 1)

        visit(data, 0)
        return payloads

    def _count_csv_rows(self, csv_path: Path) -> int:
        try:
            with open(csv_path, 'rb') as f:
                line_count = sum(1 for _ in f)
            return max(line_count - 1, 0)
        except Exception as e:
            logger.warning(f"Failed to count CSV rows: {e}")
            return 0

    async def _maybe_emit_papers_csv_artifacts(
        self,
        websocket: Any,
        agent_id: str,
        session_id: Optional[str],
        result_data: Any
    ) -> None:
        if not session_id:
            return
        if isinstance(result_data, dict):
            if result_data.get("csv_file_path") or result_data.get("csv_download_url"):
                return

        from utils.paths import get_session_path

        csv_path = get_session_path(session_id, "papers") / "all_papers.csv"
        if not csv_path.exists():
            papers_root = get_session_path(session_id, "papers").parent
            candidates = list(papers_root.glob("session_*/all_papers.csv"))
            if not candidates:
                return
            csv_path = max(candidates, key=lambda p: p.stat().st_mtime)

        total_papers = self._count_csv_rows(csv_path)
        csv_path_str = str(csv_path)
        synthetic_output = {
            "csv_file_path": csv_path_str,
            "csv_download_url": DataProcessor._build_download_url_from_path(csv_path_str),
            "total_papers_in_csv": total_papers,
            "session_id": session_id,
        }

        await DataProcessor._process_file_links(
            synthetic_output,
            agent_id,
            websocket,
            session_id
        )

        await MessageHandler.send_message(websocket, "tool_execution", {
            "agentId": agent_id,
            "sessionId": session_id,
            "toolName": "search_papers",
            "input": {"session_id": session_id},
            "output": synthetic_output,
            "status": "success",
            "timestamp": datetime.now().isoformat()
        })

    async def _maybe_emit_analysis_artifacts(
        self,
        websocket: Any,
        agent_id: str,
        session_id: Optional[str],
        result_data: Any
    ) -> None:
        if not session_id:
            return
        if isinstance(result_data, dict):
            if result_data.get("summary_file_path") or result_data.get("report_file_path"):
                return
            if result_data.get("md_download_url"):
                return
            if result_data.get("csv_file_path") and "analysis_results" in str(result_data.get("csv_file_path")):
                return

        from utils.paths import get_session_path

        papers_dir = get_session_path(session_id, "papers")
        if not papers_dir.exists():
            return

        analysis_md = None
        analysis_csv = None
        md_candidates = list(papers_dir.glob("analysis_*.md"))
        if md_candidates:
            analysis_md = max(md_candidates, key=lambda p: p.stat().st_mtime)

        csv_candidates = list(papers_dir.glob("analysis_results_*.csv"))
        if csv_candidates:
            analysis_csv = max(csv_candidates, key=lambda p: p.stat().st_mtime)

        if not analysis_md and not analysis_csv:
            return

        synthetic_output: Dict[str, Any] = {
            "session_id": session_id,
        }
        if analysis_md:
            synthetic_output["summary_file_path"] = str(analysis_md)
            synthetic_output["md_download_url"] = DataProcessor._build_download_url_from_path(str(analysis_md))
        if analysis_csv:
            synthetic_output["csv_file_path"] = str(analysis_csv)
            synthetic_output["csv_download_url"] = DataProcessor._build_download_url_from_path(str(analysis_csv))

        await DataProcessor._process_file_links(
            synthetic_output,
            agent_id,
            websocket,
            session_id
        )

        await MessageHandler.send_message(websocket, "tool_execution", {
            "agentId": agent_id,
            "sessionId": session_id,
            "toolName": "batch_paper_analysis",
            "input": {"session_id": session_id},
            "output": synthetic_output,
            "status": "success",
            "timestamp": datetime.now().isoformat()
        })

    async def _maybe_emit_database_structures_from_storage(
        self,
        websocket: Any,
        agent_id: str,
        session_id: Optional[str],
        result_data: Any,
        max_files: int = 5
    ) -> None:
        if not session_id:
            return

        if isinstance(result_data, dict):
            # 如果已经有结构数据或文件路径，说明已经处理过了，不要重复发送
            if result_data.get("structures") or result_data.get("database_structures"):
                return
            if result_data.get("frontend_structures") or result_data.get("generated_structures"):
                return
            if result_data.get("cif_file_path") or result_data.get("cif_paths"):
                return
            # 🔧 新增：如果是optimize_batch_results处理过的结果（有count但structures被移除），
            # 说明结构已经在data_processor中发送过了，不要重复加载
            if result_data.get("count") and result_data.get("database"):
                logger.info(f"⏭️ Skipping storage emission - structures already processed by data_processor")
                return

        try:
            from utils.paths import get_session_path
            from .structure_converter import StructureConverter

            database_dir = get_session_path(session_id, "database")
            if not database_dir.exists():
                return

            cif_files = sorted(
                database_dir.glob("*.cif"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            if not cif_files:
                return

            structures = []
            selected_files = cif_files[:max_files]
            for cif_path in selected_files:
                try:
                    cif_content = cif_path.read_text(encoding="utf-8", errors="ignore")
                except Exception as e:
                    logger.warning(f"?? Failed to read CIF: {cif_path} ({e})")
                    continue

                source = "Database"
                filename = cif_path.name
                if filename.startswith("MP_"):
                    source = "MP"
                elif filename.startswith("OQMD_"):
                    source = "OQMD"
                elif filename.startswith("COD_"):
                    source = "COD"
                elif filename.startswith("AFLOW_"):
                    source = "AFLOW"

                # 🔧 修复：从文件名提取化学式
                # 格式示例：
                #   OQMD_NaCl_306107_20260120_054036.cif -> NaCl
                #   MP_mp-1234_Fe2O3.cif -> Fe2O3
                #   COD_1234_NaCl.cif -> NaCl
                #   AFLOW_auid123_CaTiO3.cif -> CaTiO3
                composition = cif_path.stem
                
                # 移除数据库前缀
                for prefix in ["MP_", "OQMD_", "COD_", "AFLOW_", "Database_"]:
                    if composition.startswith(prefix):
                        composition = composition[len(prefix):]
                        break
                
                # 提取化学式部分
                parts = composition.split("_")
                if len(parts) >= 2:
                    # 如果第一部分看起来像ID（纯数字、mp-xxx、auid-xxx等），取第二部分
                    first_part_lower = parts[0].lower()
                    if (parts[0].isdigit() or 
                        first_part_lower.startswith("mp-") or 
                        first_part_lower.startswith("auid") or
                        first_part_lower.startswith("cod-")):
                        composition = parts[1] if len(parts) > 1 else parts[0]
                    else:
                        # 第一部分就是化学式
                        composition = parts[0]
                else:
                    composition = parts[0]

                converted = StructureConverter.convert_cif_to_structure(
                    cif_content=cif_content,
                    name=cif_path.stem,
                    composition=composition or cif_path.stem,
                    source=source
                )
                if converted:
                    converted["cif_file_path"] = str(cif_path)
                    # 🔧 修复：确保结构数据被标准化（统一formula字段）
                    converted = StructureConverter.standardize_structure_data(converted, source)
                    structures.append(converted)

            if not structures:
                return

            logger.info(f"?? Emitting {len(structures)} database structures from storage for {session_id}")

            await DataProcessor._process_file_links(
                {"cif_paths": [str(path) for path in selected_files]},
                agent_id,
                websocket,
                session_id
            )

            await DataProcessor._send_message(websocket, "structure_data", {
                "structures": structures,
                "agentId": agent_id,
                "sessionId": session_id,
                "timestamp": datetime.now().isoformat(),
                "total": len(structures),
                "max_display": DataProcessor.MAX_STRUCTURES
            })

        except Exception as e:
            logger.warning(f"?? Failed to emit database structures from storage: {e}")

    def _infer_tool_name_from_result(self, tool_result: Any, result_data: Any) -> Optional[str]:
        """Best-effort tool name inference from result payloads."""
        for attr in ("name", "tool_name", "toolName", "function_name", "functionName"):
            if hasattr(tool_result, attr):
                value = getattr(tool_result, attr)
                if isinstance(value, str) and value:
                    return value

        if isinstance(result_data, dict):
            for key in ("tool_name", "toolName", "tool", "name", "function_name", "functionName"):
                value = result_data.get(key)
                if isinstance(value, str) and value:
                    return value

        return None

    def _select_pending_tool_record(
        self,
        session_key: str,
        tool_result: Any = None,
        result_data: Any = None
    ) -> Optional[Dict[str, Any]]:
        """Pick the pending tool call record most likely matching the tool result."""
        records = self.current_tool_calls.get(session_key, [])
        if not records:
            return None

        inferred_name = self._infer_tool_name_from_result(tool_result, result_data)
        if inferred_name:
            for record in reversed(records):
                if record.get("status") == "pending" and record.get("name") == inferred_name:
                    return record

        for record in reversed(records):
            if record.get("status") == "pending":
                return record

        return None

    def _save_evidence_from_result(self, agent_id: str, result_data: Any, session_id: Optional[str]) -> None:
        if not session_id or not isinstance(result_data, dict):
            return

        if agent_id == "deep_research_agent":
            payload = {
                "csv_download_url": result_data.get("csv_download_url"),
                "md_download_url": result_data.get("md_download_url"),
                "csv_file_path": result_data.get("csv_file_path"),
                "summary_file_path": result_data.get("summary_file_path") or result_data.get("report_file_path"),
                "total_papers_in_csv": result_data.get("total_papers_in_csv"),
                "topic": result_data.get("topic") or result_data.get("query"),
            }
            SessionManager.save_evidence(session_id, "literature", payload)
            return

        if agent_id == "database_agent":
            structures = result_data.get("structures")
            if isinstance(structures, list) and structures:
                top = []
                for item in structures[:3]:
                    if not isinstance(item, dict):
                        continue
                    source = item.get("source") or {}
                    if not isinstance(source, dict):
                        source = {}
                    top.append({
                        "formula": item.get("formula"),
                        "id": item.get("id") or item.get("material_id"),
                        "source": source.get("database"),
                        "cif_file_path": item.get("cif_file_path") or item.get("cif_path"),
                    })
                if top:
                    SessionManager.save_evidence(session_id, "database", {"structures": top})
            return

        if agent_id == "simulation_agent":
            payload = {
                "thermal_conductivity": result_data.get("thermal_conductivity"),
                "method": result_data.get("method"),
                "temperature": result_data.get("temperature"),
                "results_file": result_data.get("results_file"),
                "batch_results_file": result_data.get("batch_results_file"),
                "phonon_dispersion_csv": result_data.get("phonon_dispersion_csv"),
                "phonon_dos_csv": result_data.get("phonon_dos_csv"),
                "cif_filename": result_data.get("cif_filename"),
            }
            SessionManager.save_evidence(session_id, "simulation", payload)
            return

    def _archive_truncated_history(
        self,
        session_id: Optional[str],
        session_key: str,
        removed_events: List[Any],
        kept_count: int,
        reason: str
    ) -> None:
        if not session_id or not removed_events:
            return
        try:
            from .session_manager import SessionManager

            sample_events = []
            if removed_events:
                head = removed_events[:3]
                tail = removed_events[-3:] if len(removed_events) > 3 else []
                sample_events = head + tail

            summary = {
                "session_id": session_id,
                "session_key": session_key,
                "reason": reason,
                "removed_count": len(removed_events),
                "kept_count": kept_count,
                "created_at": datetime.now().isoformat(),
                "samples": [self._extract_event_text(ev) for ev in sample_events]
            }

            SessionManager.save_history_summary(session_id, summary)
        except Exception as e:
            logger.warning(f"Failed to archive truncated history for {session_id}: {e}")

    def _infer_routing_targets(self, content: str) -> List[str]:
        if not content or not isinstance(content, str):
            return []

        stripped = content.strip()
        confirmations = {
            "确认", "是", "好的", "好", "继续", "开始", "可以", "执行", "确定",
            "ok", "okay", "yes", "y"
        }
        if stripped in confirmations:
            return []

        text = stripped.lower()
        targets: set[str] = set()

        literature_keywords = [
            "文献", "论文", "综述", "检索", "搜索", "参考文献", "citation",
            "arxiv", "tavily", "semantic scholar", "literature", "paper"
        ]
        database_keywords = [
            "数据库", "材料数据库", "结构", "晶体", "材料属性", "材料性质",
            "materials project", "oqmd", "cod", "aflow", "mp-"
        ]
        simulation_keywords = [
            "仿真", "计算", "声子", "热导率", "弛豫", "能量", "kappa",
            "phonon", "relax", "simulation"
        ]
        experiment_keywords = [
            "实验方案", "实验设计", "验证路线", "验证方案", "实验计划", "实验"
        ]

        if any(k in text for k in literature_keywords):
            targets.add("deep_research_agent")
        if any(k in text for k in database_keywords):
            targets.add("database_agent")
        if any(k in text for k in simulation_keywords):
            targets.add("simulation_agent")
        if any(k in text for k in experiment_keywords):
            targets.add("experiment_plan_agent")

        return list(targets)



    async def process_chat_message(

        self,

        client_id: str,

        websocket: Any,

        content: str,

        agent_id: str,

        session_id: Optional[str] = None,

        retry_count: int = 0,

        attachments: Optional[List[Dict[str, Any]]] = None,

        allow_router: bool = True

    ) -> None:

        """

        Process chat message with specified agent



        Args:

            client_id: Client ID

            websocket: WebSocket connection

            content: Message content

            agent_id: Agent ID to use

            session_id: Optional session ID

            retry_count: Number of retries attempted

        """

        max_retries = 1  # 最多重息息
        session_key: Optional[str] = None

        try:

            # Get agent instance

            adk_agent = self.agents.get(agent_id)

            if not adk_agent:

                await MessageHandler.send_error(websocket, f"Unknown agent: {agent_id}")

                return

            if not session_id:
                await MessageHandler.send_error(websocket, "Session ID is required")
                return

            # Router fallback for research coordinator
            if allow_router and agent_id == "research_coordinator":
                targets = self._infer_routing_targets(content)
                if targets:
                    if "experiment_plan_agent" in targets:
                        ordered_targets = ["experiment_plan_agent"]
                    else:
                        preferred_order = ["database_agent", "simulation_agent", "deep_research_agent"]
                        ordered_targets = [t for t in preferred_order if t in targets]
                        if not ordered_targets:
                            ordered_targets = targets

                    name_map = {
                        "deep_research_agent": "文献研究助手",
                        "database_agent": "数据库查询助手",
                        "simulation_agent": "仿真计算助手",
                        "experiment_plan_agent": "实验方案推荐",
                    }

                    for target_agent in ordered_targets:
                        await MessageHandler.send_message(websocket, "status", {
                            "status": "info",
                            "message": f"已自动转交给{name_map.get(target_agent, target_agent)}处理",
                            "agentId": target_agent,
                            "sessionId": session_id
                        })
                        await self.process_chat_message(
                            client_id=client_id,
                            websocket=websocket,
                            content=content,
                            agent_id=target_agent,
                            session_id=session_id,
                            retry_count=retry_count,
                            attachments=attachments,
                            allow_router=False
                        )
                    return



            # Create session key

            session_key = f"{client_id}_{agent_id}_{session_id or 'default'}"

            # 🆕 Shared history key should be stable across reconnects/devices

            # Use session_id only to avoid coupling with client_id

            history_key = f"{session_id or 'default'}"



            # 🆕 清除停止标志（开始新的处理）

            self.clear_stop_flag(session_key)



            # Create or get session

            if session_key not in self.session_services:

                await self._create_session(session_key, client_id, adk_agent, session_id)



            session = self.adk_sessions[session_key]

            runner = self.runners[session_key]



            # 🆕 登记当前活跃任务，便于 stop 时取消

            try:

                current_task = asyncio.current_task()

                if current_task:

                    self.active_tasks[session_key] = current_task

            except Exception:

                pass



            # 🆕 Sync history from shared storage to ensure cross-agent context

            # Primary: session_id-only key (stable).

            restored_history = self._restore_history_from_disk(history_key)

            if restored_history:

                # Google ADK Session uses 'events' not 'history'

                if hasattr(session, 'events'):

                    session.events = restored_history

                self.session_message_counts[session_key] = len(restored_history)

                logger.info(f"🔄 Synced history for {session_key} from {history_key} ({len(restored_history)} messages)")



            # 检查会话消息数息

            message_count = self.session_message_counts.get(session_key, 0)



            # 如果超过最大消息数，截断历息

            if message_count >= MAX_CONTEXT_MESSAGES:

                logger.warning(f"⚠️ Session {session_key} has {message_count} messages. Truncating history...")

                await self._truncate_session_history(
                    session_key,
                    websocket,
                    session_id=session_id,
                    reason="max_limit"
                )

                message_count = self.session_message_counts.get(session_key, 0)



            # 🆕 如果超过自动清理阈值，主动清理（避免等到超限才清理息

            elif message_count >= CONTEXT_AUTO_CLEAR_THRESHOLD:

                logger.warning(f"⚠️ Session {session_key} has {message_count} messages. Auto-clearing to avoid overflow...")

                await self._truncate_session_history(
                    session_key,
                    websocket,
                    target_count=8,
                    session_id=session_id,
                    reason="auto_clear"
                )

                message_count = self.session_message_counts.get(session_key, 0)

                await MessageHandler.send_message(

                    websocket,

                    "status",

                    {

                        "status": "info",

                        "message": f"💡 已自动清理旧消息以避免上下文超限（保留最近{message_count}条）"

                    }

                )



            # 如果接近上下文限制，发送警息

            elif message_count >= CONTEXT_SUMMARY_THRESHOLD:

                logger.warning(f"⚠️ Session {session_key} has {message_count} messages. Approaching context limit.")

                await MessageHandler.send_message(

                    websocket,

                    "status",

                    {

                        "status": "warning",

                        "message": f"💡 对话历史较长（{message_count}条），将在更多消息后自动清理"

                    }

                )



            # 增加消息计数

            self.session_message_counts[session_key] = message_count + 1



            # 记录消息开始时的统计状态（用于计算本条消息的增量）

            from services.user_billing_config import get_billing_context_manager

            context_manager = get_billing_context_manager()

            # 优先使用已认证的用户 ID；否则回退息session_id

            conversation_id = session_id or 'unknown'

            try:

                from .websocket_server import WebSocketServer

                ws = WebSocketServer.get_instance()

                authed_user_id = None

                if ws and client_id in ws.client_sessions:

                    authed_user_id = ws.client_sessions[client_id].get("authenticated_user_id")

                user_id = str(authed_user_id) if authed_user_id else (session_id or 'unknown')

                logger.info(f"🔍 [统计] authed_user_id={authed_user_id}, user_id={user_id}, session_id={session_id}, client_id={client_id}")

            except Exception as e:

                logger.warning(f"⚠️ 获取认证用户 ID 失败: {e}")

                user_id = session_id or 'unknown'



            context = context_manager.get_or_create_context(conversation_id, user_id)

            start_snapshot = context.get_snapshot()



            self.message_start_billing[session_key] = {

                'total_tokens': start_snapshot.get('total_tokens', 0),

                'conversation_id': conversation_id,

                'user_id': user_id,

                'client_id': client_id

            }

            logger.info(f"📊 [消息统计] 消息开始时统计状息")

            logger.info(f"  session_key={session_key}")

            logger.info(f"  conversation_id={conversation_id}")

            logger.info(f"  start_snapshot={start_snapshot}")

            logger.info(f"  message_start_billing[{session_key}]={self.message_start_billing[session_key]}")



            # Run agent

            logger.info(f"🤖 Running agent: {agent_id} (message #{self.session_message_counts[session_key]})")



            # 创建用户消息 - 需要使息types.Content 包装 types.Part

            parts = []



            # 🔧 对于 deep_research_agent 息simulation_agent，在消息开头添息session_id 信息

            # 这样 Agent 可以在所有操作中使用相同息session_id，避免使息default

            if agent_id in ['deep_research_agent', 'simulation_agent', 'database_agent'] and session_id:

                session_info = f"[系统信息] 当前会话 session_id=\"{session_id}\"，所有工具调用必须使用此 session_id\n\n"

                parts.append(types.Part(text=session_info))



            parts.append(types.Part(text=content))



            # Attach optional file/text parts (e.g., CIF content) so agents can parse them

            if attachments:

                # 对于 deep_research_agent 息simulation_agent，保存文件到磁盘

                # 支持两种格式息

                # 1. base64 编码的文件（encoding='base64'息

                # 2. 纯文本文件（息CIF 文件，直接包息content 字符串）

                if agent_id in ['deep_research_agent', 'simulation_agent']:

                    import json

                    import base64

                    from pathlib import Path



                    # 确保 session_id 存在（如果为 None，生成一个唯一的）

                    from utils.session import ensure_session_id

                    actual_session_id = ensure_session_id(session_id)

                    if not session_id:

                        logger.info(f"?? Generated session_id for file upload: {actual_session_id}")



                    # 根据 agent 类型选择不同的上传目息- 使用统一存储

                    import sys

                    from pathlib import Path as PathLib



                    # 添加 mcp_servers/shared 息sys.path

                    shared_path = PathLib(__file__).parent.parent / "mcp_servers" / "shared"

                    if str(shared_path) not in sys.path:

                        sys.path.insert(0, str(shared_path))



                    # 导入 storage_manager

                    from storage_manager import get_session_storage_path



                    if agent_id == 'deep_research_agent':

                        # 文献研究 agent 使用 papers 目录

                        upload_dir = get_session_storage_path(

                            session_id=actual_session_id,

                            data_type="papers",

                            create=True,

                            session_type="upload",

                            created_by="user",

                            topic=None  # 上传时通常没有明确息topic

                        ) / "uploads"

                    elif agent_id == 'simulation_agent':

                        # 模拟 agent 使用 cif 目录

                        upload_dir = get_session_storage_path(

                            session_id=actual_session_id,

                            data_type="cif",

                            create=True,

                            session_type="upload",

                            created_by="user",

                            topic=None

                        )

                    else:

                        # 默认使用 papers 目录

                        upload_dir = get_session_storage_path(

                            session_id=actual_session_id,

                            data_type="papers",

                            create=True,

                            session_type="upload",

                            created_by="user",

                            topic=None

                        ) / "uploads"



                    upload_dir.mkdir(parents=True, exist_ok=True)



                    # 🆕 导入文件名清理函数，确保息MCP 工具使用相同的文件名

                    import re



                    def _sanitize_filename(filename: str) -> str:

                        """清理文件名,与uploaded_documents.py保持一致"""

                        sanitized = re.sub(r'[<>:"/\\|?*]+', "_", filename)

                        sanitized = re.sub(r'[\s_]+', "_", sanitized)

                        sanitized = sanitized.strip("_")

                        if not sanitized:

                            sanitized = "uploaded_document"

                        if len(sanitized) > 200:

                            sanitized = sanitized[:200]

                        return sanitized



                    saved_files = []

                    for att in attachments:

                        original_filename = att.get('filename', 'document.txt')

                        # 🆕 使用清理后的文件名，避免息MCP 工具重复保存

                        filename = _sanitize_filename(original_filename)



                        # 处理 base64 编码的文息

                        if att.get('encoding') == 'base64':

                            content_b64 = att.get('content', '')

                            try:

                                file_bytes = base64.b64decode(content_b64)

                                file_path = upload_dir / filename



                                # 🔧 修复：如果文件已存在，使用时间戳避免覆盖，保持原始文件名结构

                                if file_path.exists():

                                    from datetime import datetime

                                    base_name = file_path.stem

                                    suffix = file_path.suffix

                                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                                    file_path = upload_dir / f"{base_name}_{timestamp}{suffix}"

                                    logger.info(f"File already exists, using timestamped name: {file_path.name}")



                                file_path.write_bytes(file_bytes)



                                saved_files.append({

                                    'filename': original_filename,  # 保留原始文件名用于显息

                                    'saved_filename': file_path.name,  # 🔧 修复：使用实际保存的文件息

                                    'path': str(file_path),

                                    'size': len(file_bytes),

                                    'mime_type': att.get('mime_type', 'application/octet-stream')

                                })

                                logger.info(f"💾 Saved base64 file: {original_filename} -> {file_path.name} ({len(file_bytes)} bytes)")

                            except Exception as e:

                                logger.error(f"息Failed to save base64 file {original_filename}: {e}")

                                continue



                        # 处理纯文本文件（息CIF 文件息

                        else:

                            text_content = att.get('content', '')

                            if text_content:

                                try:

                                    file_path = upload_dir / filename



                                    # 🔧 修复：如果文件已存在，使用时间戳避免覆盖，保持原始文件名结构

                                    if file_path.exists():

                                        from datetime import datetime

                                        base_name = file_path.stem

                                        suffix = file_path.suffix

                                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                                        file_path = upload_dir / f"{base_name}_{timestamp}{suffix}"

                                        logger.info(f"File already exists, using timestamped name: {file_path.name}")



                                    file_path.write_text(text_content, encoding='utf-8')



                                    saved_files.append({

                                        'filename': original_filename,  # 保留原始文件名用于显息

                                        'saved_filename': file_path.name,  # 🔧 修复：使用实际保存的文件息

                                        'path': str(file_path),

                                        'size': len(text_content.encode('utf-8')),

                                        'mime_type': att.get('mime_type', 'text/plain')

                                    })

                                    logger.info(f"💾 Saved text file: {original_filename} -> {file_path.name} ({len(text_content)} chars)")

                                except Exception as e:

                                    logger.error(f"息Failed to save text file {original_filename}: {e}")

                                    continue



                    if saved_files:

                        # 只传递文件元数据（不包含内容），引导 agent 使用工具

                        file_info = f"\n\n用户上传息{len(saved_files)} 个文件：\n"

                        for f in saved_files:

                            size_kb = f['size'] / 1024

                            file_info += f"- {f['filename']} ({size_kb:.2f}KB): `{f['path']}`\n"  # 🆕 Added file path

                        file_info += f"\n文件已保存到：{upload_dir}\n"



                        # 根据 agent 类型提供不同的工具调用提息

                        if agent_id == 'deep_research_agent':

                            file_info += f"\n⚠️ 请立即调用工具：ingest_uploaded_papers(session_id=\"{actual_session_id}\")"

                            file_info += f"\n注意：session_id 必须使用引号中的值：\"{actual_session_id}\""

                        elif agent_id == 'simulation_agent':

                            # 检查是否有 CIF 文件

                            cif_files = [f for f in saved_files if f['filename'].lower().endswith('.cif')]

                            if cif_files:

                                file_info += f"\n⚠️ 检测到 CIF 文件，请调用工具：extract_and_validate_cif(session_id=\"{actual_session_id}\")"

                                file_info += f"\n注意：session_id 必须使用引号中的值：\"{actual_session_id}\""



                        parts.append(types.Part(text=file_info))

                else:

                    # 其他 agent 或纯文本附件：直接附加文本内息

                    for att in attachments:

                        fname = att.get('filename') or 'attachment.txt'

                        text = att.get('content') or ''

                        # Prefix to help agent tools detect attachment context

                        att_text = f"[附件: {fname}]\n{text}"

                        parts.append(types.Part(text=att_text))

            user_message = types.Content(role='user', parts=parts)



            # 设置线程本地存储息session 上下文，息callbacks 使用

            # 🔴 修复：使息session_id 作为 user_id，而不息client_id

            # session_id 是用户的真实标识（与计费配置关联），client_id 只是 WebSocket 连接标识

            # 🔧 同时传息client_id 作为回退查找配置的依息

            from agents.callbacks import set_current_session_context

            set_current_session_context(session_id or 'unknown', user_id, client_id)

            logger.info(f"🔍 [AGENT_COORDINATOR] 设置 session 上下息 session_id={session_id}, user_id={user_id}, client_id={client_id}")



            # Google ADK API: run_async() 需息user_id, session_id 息new_message 参数


            import asyncio

            event_count = 0

            async def process_events():
                nonlocal event_count
                async for event in runner.run_async(
                    user_id=client_id,
                    session_id=session.id,
                    new_message=user_message
                ):
                    # Check stop flag
                    if self.should_stop(session_key):
                        logger.info(f"Stop flag detected, aborting {session_key}")
                        self.clear_stop_flag(session_key)
                        await MessageHandler.send_message(
                            websocket,
                            "status",
                            {
                                "status": "stopped",
                                "message": "Stopped"
                            }
                        )
                        return

                    event_count += 1
                    logger.info(f"🔍 [Event {event_count}] Type: {type(event).__name__}")
                    logger.info(f"🔍 [Event {event_count}] Attributes: {[attr for attr in dir(event) if not attr.startswith('_')]}")

                    await self._handle_agent_event(event, agent_id, websocket, client_id, session_id)
                    self._persist_history_snapshot(session_id, session)

            await process_events()

            logger.info(f"Agent {agent_id} completed - processed {event_count} events")

            # 获取会话的统计数据（使用隔离上下文）
            from .user_billing_config import get_billing_context_manager

            context_manager = get_billing_context_manager()

            # 使用 session_id 获取隔离的统计上下文
            billing_session_key = session_id or 'unknown'
            context = context_manager.get_context(billing_session_key)

            # 息ConversationBillingContext 获取统计信息
            session_usage = {
                'total_tokens': 0,
                'total_photons_charged': 0,
                'requests_count': 0,
                'feature_charges': []
            }

            if context:
                # 从隔离上下文获取统计数据
                snapshot = context.get_snapshot()
                session_usage = {
                    'total_tokens': snapshot['total_tokens'],
                    'total_photons_charged': snapshot['total_photons_charged'],
                    'requests_count': snapshot['request_count'],
                    'feature_charges': snapshot.get('feature_charges', [])
                }

            logger.info(f"📊 [统计] 会话累计: {session_usage.get('total_tokens', 0)} tokens (仅供参息 | 已扣息 {session_usage.get('total_photons_charged', 0)} 光子 | 请求次数: {session_usage.get('requests_count', 0)}")

            # 发送完成状态（包含统计信息息
            billing_data = {
                "session_total_tokens": session_usage.get('total_tokens', 0),  # Token 统计（仅供参考）
                "session_total_photons": session_usage.get('total_photons_charged', 0),  # 🔧 修复：字段名改为 session_total_photons（前端期望的字段名）
                "requests_count": session_usage.get('requests_count', 0),
                "model_name": os.getenv('MODEL_USE', 'qwen-plus'),
                "feature_charges": session_usage.get('feature_charges', []),  # 功能扣费明细
                "charged": session_usage.get('total_photons_charged', 0) > 0,  # 🆕 是否已扣费（光子息> 0息
                "billing_source": "Cookie"  # 🆕 计费来源
            }

            logger.info(f"📤 [WebSocket] 准备发息complete 状态，统计数据: {billing_data}")

            await MessageHandler.send_message(websocket, "status", {
                "status": "complete",
                "message": "Agent completed.",
                "billing": billing_data,
            })
            self._stop_task_heartbeat(session_key)

            try:
                session_events = getattr(session, 'events', None) or []
                if session_events:
                    stable_key = f"{session_id or 'default'}"
                    HybridSessionManager.save_history(stable_key, session_events)
                    logger.info(f"Saved {len(session_events)} events for {stable_key}")
            except Exception as e:
                logger.error(f"Failed to save history for {session_id or 'default'}: {e}")

            logger.info(f"息Agent {agent_id} completed")



        

        except asyncio.CancelledError:
            logger.info(f"🛑 Task cancelled for session: {session_key}")
            await MessageHandler.send_message(websocket, "status", {
                "status": "stopped",
                "message": "任务已停止。",
            })
            self._stop_task_heartbeat(session_key)
            if session_key:
                self._persist_history_for_session_key(session_key, reason="error")
            if session_key:
                self._persist_history_for_session_key(session_key, reason="task_cancelled")
            return
        except Exception as e:

            error_msg = str(e)
            self._stop_task_heartbeat(session_key)

            logger.error(f"息Agent processing error: {error_msg}", exc_info=True)

            # 如果存在 pending 的工具调用，补发 error 以避免前端卡住
            try:
                pending_tool = None
                if session_key in self.current_tool_calls and self.current_tool_calls[session_key]:
                    for tool_call_record in reversed(self.current_tool_calls[session_key]):
                        if tool_call_record.get("status") == "pending":
                            tool_call_record["status"] = "error"
                            tool_call_record["error"] = error_msg
                            pending_tool = tool_call_record
                            break

                if pending_tool:
                    await MessageHandler.send_message(websocket, "tool_execution", {
                        "agentId": agent_id,
                        "sessionId": session_id,
                        "toolName": pending_tool.get("name"),
                        "input": pending_tool.get("input"),
                        "status": "error",
                        "error": error_msg,
                        "timestamp": pending_tool.get("timestamp") or datetime.now().isoformat()
                    })
            except Exception as tool_error:
                logger.warning(f"⚠️ Failed to mark pending tool as error: {tool_error}")



            # Check for JSON parsing errors from LLM tool calls

            if "JSONDecodeError" in error_msg or "Expecting ',' delimiter" in error_msg:

                logger.error(f"息JSON parsing error in LLM tool call - this may be a DeepSeek formatting issue")

                await MessageHandler.send_error(
                    websocket,
                    "LLM returned a malformed tool call. Please retry or switch to the Gemini model.",
                )

                return



            # 检查是否是上下文窗口超限错息

            if "ContextWindowExceededError" in error_msg or "context length" in error_msg.lower():

                logger.warning(f"⚠️ Context window exceeded, truncating session: {session_key}")



                # 截断历史

                await self._truncate_session_history(
                    session_key,
                    websocket,
                    session_id=session_id,
                    reason="context_window_exceeded"
                )



                # 提示用户

                await MessageHandler.send_error(
                    websocket,
                    "Context window exceeded. Old messages were cleared; please resend your query or start a new session.",

                )

                return



            # 检查是否是LLM服务端错误（空响应/非法JSON）
            if "InternalServerError" in error_msg or "OpenAIException" in error_msg or "Expecting value" in error_msg:
                if retry_count < max_retries:
                    backoff = 1 + retry_count
                    logger.info(f"🔄 Retrying LLM request (attempt {retry_count + 1}/{max_retries}) after {backoff}s...")
                    await MessageHandler.send_message(
                        websocket,
                        "status",
                        {
                            "status": "retrying",
                            "message": "LLM 服务异常，正在重试...",
                            "agent_id": agent_id
                        }
                    )
                    import asyncio
                    await asyncio.sleep(backoff)
                    await self.process_chat_message(
                        client_id=client_id,
                        websocket=websocket,
                        content=content,
                        agent_id=agent_id,
                        session_id=session_id,
                        retry_count=retry_count + 1,
                        allow_router=allow_router
                    )
                    return
                await MessageHandler.send_error(
                    websocket,
                    "LLM service error. Please retry later.",
                )
                return

            # 检查是否是MCP连接错误

            if "Connection closed" in error_msg or "ReadTimeout" in error_msg:

                # MCP连接错误，清理session

                logger.warning(f"🔄 MCP connection error detected, clearing session: {session_key}")

                self.clear_session(client_id, agent_id, session_id)



                # 如果还没有重试过，自动重试一息

                if retry_count < max_retries:

                    logger.info(f"🔄 Retrying request (attempt {retry_count + 1}/{max_retries})...")

                    await MessageHandler.send_message(

                        websocket,

                        "status",

                        {

                            "status": "retrying",

                            "message": "连接超时，正在自动重息..",

                            "agent_id": agent_id

                        }

                    )



                    # 等待1秒后重试

                    import asyncio

                    await asyncio.sleep(1)



                    # 递归调用，增加retry_count

                    await self.process_chat_message(

                        client_id=client_id,

                        websocket=websocket,

                        content=content,

                        agent_id=agent_id,

                        session_id=session_id,

                        retry_count=retry_count + 1,

                        allow_router=allow_router

                    )

                else:

                    # 已经重试过，发送错误消息

                    await MessageHandler.send_error(
                        websocket,
                        "Database connection timed out. Please retry later or reduce the query scope.",
                    )

            else:

                # 其他错误

                await MessageHandler.send_error(websocket, f"处理失败: {error_msg}")

    def _ensure_tool_calls_completeness(self, events: List[Any]) -> List[Any]:
        """
        确保事件列表中的 tool_calls 都有对应的 tool 响应。
        如果最后一条 assistant 消息包含 tool_calls 但后面没有 tool 响应，
        则移除这条消息及其之后的所有消息，避免 OpenAI API 错误。
        
        Args:
            events: 事件列表
            
        Returns:
            修正后的事件列表
        """
        if not events:
            return events
        
        try:
            # 从后向前扫描，查找未配对的 tool_calls
            i = len(events) - 1
            while i >= 0:
                event = events[i]
                role = getattr(event, 'role', None)
                
                # 如果是 assistant 消息
                if role == 'assistant':
                    # 检查是否有 tool_calls
                    has_tool_calls = False
                    if hasattr(event, 'tool_calls') and event.tool_calls:
                        has_tool_calls = True
                    elif hasattr(event, 'get_function_calls'):
                        try:
                            tool_calls = event.get_function_calls()
                            if tool_calls:
                                has_tool_calls = True
                        except:
                            pass
                    
                    if has_tool_calls:
                        # 检查后面是否有对应的 tool 响应
                        has_tool_response = False
                        for j in range(i + 1, len(events)):
                            next_event = events[j]
                            next_role = getattr(next_event, 'role', None)
                            if next_role == 'tool':
                                has_tool_response = True
                                break
                            elif next_role in ['assistant', 'user']:
                                # 如果遇到新的 assistant 或 user 消息，说明没有 tool 响应
                                break
                        
                        if not has_tool_response:
                            # 移除这条 tool_calls 消息及其之后的所有消息
                            logger.warning(f"⚠️ Removing incomplete tool_calls at position {i} (no tool response found)")
                            return events[:i]
                    
                    # 找到第一条完整的 assistant 消息，停止搜索
                    break
                
                i -= 1
            
            return events
            
        except Exception as e:
            logger.error(f"❌ Error in _ensure_tool_calls_completeness: {e}", exc_info=True)
            return events

    async def _truncate_session_history(

        self,

        session_key: str,

        websocket: Any,

        target_count: Optional[int] = None,
        session_id: Optional[str] = None,
        reason: str = "truncate"

    ) -> None:

        """

        Truncate session history to keep only recent messages



        Args:

            session_key: Session key

            websocket: WebSocket connection for notifications

            target_count: Optional target message count (default: MAX_CONTEXT_MESSAGES)

        """

        try:

            session = self.adk_sessions.get(session_key)

            if not session:

                return



            # Get current history (Google ADK uses 'events')

            history = getattr(session, 'events', None) or []

            current_count = len(history)



            # 使用指定息target_count 或默认息

            keep_target = target_count if target_count else MAX_CONTEXT_MESSAGES



            if current_count > keep_target:

                # Keep only the most recent messages

                # Keep system message (first) + recent messages

                keep_count = keep_target - 1  # -1 for system message
                removed_events: List[Any] = []



                if len(history) > 0 and hasattr(history[0], 'role') and history[0].role == 'system':

                    # Keep system message + recent messages

                    if hasattr(session, 'events'):

                        if keep_count > 0:
                            removed_events = history[1:-keep_count]
                            new_events = [history[0]] + history[-keep_count:]
                        else:
                            removed_events = history[1:]
                            new_events = [history[0]]
                        
                        # 🔧 修复：确保不会截断未完成的 tool_calls
                        # 检查保留的最后一条消息是否是 tool_calls，如果是，则需要回溯到上一个完整的对话轮次
                        new_events = self._ensure_tool_calls_completeness(new_events)
                        session.events = new_events

                else:

                    # Just keep recent messages

                    if hasattr(session, 'events'):

                        if keep_target > 0:
                            removed_events = history[:-keep_target]
                            new_events = history[-keep_target:]
                        else:
                            removed_events = history[:]
                            new_events = []
                        
                        # 🔧 修复：确保不会截断未完成的 tool_calls
                        new_events = self._ensure_tool_calls_completeness(new_events)
                        session.events = new_events



                new_history = getattr(session, 'events', None) or []

                removed_count = current_count - len(new_history)

                logger.info(f"✂️ Truncated session {session_key}: removed {removed_count} old messages, kept {len(new_history)}")



                # Update message count

                self.session_message_counts[session_key] = len(new_history)
                self._archive_truncated_history(session_id, session_key, removed_events, len(new_history), reason)
                self._persist_history_snapshot(session_id, session)



                # Notify user (only for explicit truncation, not auto-clear)

                if not target_count:

                    new_history = getattr(session, 'events', None) or []

                    await MessageHandler.send_message(

                        websocket,

                        "status",

                        {

                            "status": "info",

                            "message": f"Auto-cleared {removed_count} old messages; kept {len(new_history)}.",

                        }

                    )



        except Exception as e:

            logger.error(f"息Failed to truncate session history: {e}", exc_info=True)





    async def _create_session(

        self,

        session_key: str,

        client_id: str,

        adk_agent: Any,

        session_id: Optional[str] = None

    ) -> None:

        """Create new session for agent"""

        logger.info(f"🆕 Creating new session: {session_key}")



        session_service = InMemorySessionService()

        self.session_services[session_key] = session_service



        # 🔧 修复：在 state 中传递变量，息Google ADK 息instruction 模板使用

        # Google ADK 息instructions_utils.inject_session_state() 会查息state 中的变量

        # 并替息instruction 中的 {+variable_name+} 模板

        initial_state = {

            # 提供常用的上下文变量，避息KeyError

            'composition': '',  # 化学式（simulation_agent 可能用到息

            'topic': '',  # 研究主题（deep_research_agent 可能用到息

            'query': '',  # 查询关键息

            'generation_id': '',  # 结构生成 ID（simulation_agent 可能用到息

        }

        if session_id:

            initial_state['session_id'] = session_id
            self.session_id_map[session_key] = session_id

            logger.info(f"🔍 [SESSION_STATE] 设置 session_id={session_id} 息ADK session state")



        # Create ADK Session

        session = await session_service.create_session(

            app_name="ResearchMind",

            user_id=client_id,

            session_id=f"session_{session_key}",

            state=initial_state

        )

        self.adk_sessions[session_key] = session



        # Create Runner

        runner = Runner(

            agent=adk_agent,

            app_name="ResearchMind",

            session_service=session_service

        )

        self.runners[session_key] = runner



        # 🆕 Try to load history from disk using a stable key

        # Primary: session_id-only key (stable across devices/clients)

        history_key = f"{session_id or 'default'}"

        restored_history = self._restore_history_from_disk(history_key)

        if restored_history:

            # Google ADK Session uses 'events' not 'history'

            if hasattr(session, 'events'):

                session.events = restored_history

            self.session_message_counts[session_key] = len(restored_history)

            logger.info(f"♻️ Restored {len(restored_history)} messages for session {session_key} from {history_key}")

        else:

            self.session_message_counts[session_key] = 0



    def _get_tool_friendly_message(self, tool_name: str) -> str:

        """

        根据工具名称生成友好的提示信息



        Args:

            tool_name: 工具名称



        Returns:

            友好的提示信息

        """

        # 工具名称到友好提示的映射

        tool_messages = {

            # 文献搜索工具

            "search_papers": "🔍 正在搜索相关论文...",

            "search_arxiv_papers": "📚 正在ArXiv搜索论文...",

            "search_papers_all_sources": "🌐 正在多源搜索论文（ArXiv + Tavily息..",

            "tavily_search": "🔎 正在Tavily搜索...",

            "tavily_academic_search": "🎓 正在Tavily学术搜索...",

            "generate_research_plan": "📋 正在生成研究计划...",

            "batch_paper_analysis": "📊 正在批量分析论文...",

            "generate_research_report": "📝 正在生成研究报告...",

            "download_paper": "⬇️ 正在下载论文PDF...",

            "get_arxiv_paper_content": "📄 正在提取论文全文...",

            "ingest_papers_to_vector_store": "💾 正在向量化存储论息..",

            "semantic_search_papers": "🔍 正在语义搜索论文...",



            # 数据库查询工息

            "query_materials_project": "🗄息正在查询Materials Project数据息..",

            "query_oqmd": "🗄息正在查询OQMD数据息..",

            "query_cod": "🗄息正在查询COD数据息..",

            "query_aflow": "🗄息正在查询AFLOW数据息..",



            # 仿真计算工具

            "generate_crystal_structure": "🔬 正在生成晶体结构...",

            "calculate_thermal_conductivity": "🌡息正在计算热导息..",

            "calculate_phonon_spectrum": "📈 正在计算声子息..",

            "optimize_structure": "⚙️ 正在优化结构...",

        }



        # 返回友好提示，如果没有映射则返回默认提示

        return tool_messages.get(tool_name, f"🔧 正在调用工具: {tool_name}...")



    async def _charge_for_tool_if_needed(

        self,

        tool_name: str,

        session_id: str,

        user_id: Optional[str] = None,

        user_access_key: Optional[str] = None,

        user_client_name: Optional[str] = None,

        tool_args: Optional[Dict[str, Any]] = None

    ) -> Dict[str, Any]:

        """

        在工具调用前检查是否需要扣费,并执行扣费



        Args:

            tool_name: 工具名称

            session_id: 会话 ID

            user_id: 用户 ID(可选)

            user_access_key: 用户访问密钥(可选)

            user_client_name: 用户客户端名称(可选)

            tool_args: 工具参数(可选,用于计算批量数量)



        Returns:

            扣费结果字典,包含 success, message, photons 等字段

        """

        # 检查工具是否需要扣息

        try:

            from .config import billing_flags as _billing_flags

        except Exception:

            _billing_flags = None

        if _billing_flags and getattr(_billing_flags, 'POSTPAID_BILLING', False):

            feature_type = TOOL_FEATURE_MAPPING.get(tool_name)

            return {"success": True, "message": "postpaid mode - skip precharge", "photons": 0, "feature_type": feature_type}

        feature_type = TOOL_FEATURE_MAPPING.get(tool_name)

        

        # 确保 tool_args 是字息

        if tool_args is None:

            tool_args = {}



        if not feature_type:

            # 免费工具，无需扣费

            logger.debug(f"🆓 工具 {tool_name} 是免费工具，无需扣费")

            return {

                "success": True,

                "message": "免费工具",

                "photons": 0,

                "feature_type": None

            }



        # 需要扣费的工具

        try:

            logger.info(f"💰 工具 {tool_name} 需要扣费，功能类型: {feature_type}")



            # 计算扣费数量

            quantity = 1

            

            # 针对批量工具动态计算数息

            if tool_name in ['calculate_phonon_from_directory', 'calculate_kappa_from_directory']:

                # 1. 优先检查是否指定了文件列表

                cif_filenames = tool_args.get('cif_filenames')

                if cif_filenames and isinstance(cif_filenames, list) and len(cif_filenames) > 0:

                    quantity = len(cif_filenames)

                    logger.info(f"Batch tool {tool_name} specified {quantity} files.")

                else:

                    # 2. 尝试确定目录并计算文件数

                    target_dir = None

                    cif_directory = tool_args.get('cif_directory') or tool_args.get('directory')

                    

                    if cif_directory:

                        target_dir = cif_directory

                    elif session_id:

                        # 尝试根据 source_type 息session_id 解析目录

                        source_type = tool_args.get('source_type', 'uploaded') # 默认息uploaded (与工具定义一息

                        

                        try:

                            # 动态导息storage_manager

                            import sys

                            from pathlib import Path as PathLib

                            

                            # 确保 mcp_servers/shared 息sys.path 息

                            shared_path = PathLib(__file__).parent.parent / "mcp_servers" / "shared"

                            if str(shared_path) not in sys.path:

                                sys.path.insert(0, str(shared_path))

                                

                            from storage_manager import get_session_storage_path

                            

                            if source_type == "relaxed":

                                path = get_session_storage_path(session_id=session_id, data_type="relaxed_structures", create=False)

                                if path.exists():

                                    target_dir = str(path)

                            elif source_type == "uploaded":

                                path = get_session_storage_path(session_id=session_id, data_type="uploads", create=False)

                                if path.exists():

                                    target_dir = str(path)

                        except Exception as e:

                            logger.warning(f"⚠️ 解析会话目录失败: {e}")



                    # 3. 如果找到了目录，计算其中息CIF 文件息

                    if target_dir:

                        try:

                            abs_target_dir = os.path.abspath(target_dir)

                            if os.path.exists(abs_target_dir) and os.path.isdir(abs_target_dir):

                                cif_files = [f for f in os.listdir(abs_target_dir) if f.lower().endswith('.cif')]

                                quantity = len(cif_files)

                                if quantity == 0:

                                    quantity = 1 # 避免息0

                                logger.info(f"Batch tool {tool_name} specified {quantity} files.")

                            else:

                                logger.warning(f"Directory not found: {target_dir}; defaulting to quantity=1.")

                        except Exception as e:

                            logger.error(f"Failed to count files in directory: {e}; defaulting to quantity=1.")

                    else:

                        logger.warning("Unable to determine target directory; defaulting to quantity=1.")

            

            elif tool_name in ['batch_calculate_kappa', 'calculate_kappa', 'calculate_phonon', 'relax_structure', 'calculate_energy']:
                structures = tool_args.get('structures')
                if isinstance(structures, list):
                    quantity = len(structures)
                    if quantity == 0:
                        quantity = 1
                    logger.info(f"Batch tool {tool_name} specified {quantity} structures.")



            # 调用扣费服务

            result = PricingService.charge_for_feature(

                feature_type=feature_type,

                session_id=session_id,

                user_id=user_id,

                user_access_key=user_access_key,

                user_client_name=user_client_name,

                quantity=quantity

            )



            # 🆕 记录扣费到会话的计费上下文（无论成功或失败都记录息

            try:

                from services.user_billing_config import get_billing_context_manager

                context_manager = get_billing_context_manager()

                conversation_id = session_id or 'unknown'



                # 获取或创建计费上下文

                context = context_manager.get_or_create_context(

                    conversation_id=conversation_id,

                    user_id=user_id or 'unknown'

                )



                photons = result.get("photons", 0)

                success = result.get("success", False)

                error_msg = result.get("message", "未知错误")



                # 记录功能扣费（包含成息失败状态）

                context.record_feature_charge(

                    feature_type=feature_type,

                    photons=photons,

                    success=success,

                    error_message=None if success else error_msg

                )



                if success:

                    logger.info(f"息扣费成功: {tool_name} ({feature_type}) = {photons} 光子")

                    logger.info(f"📝 已记录扣费到会话 {conversation_id}: {feature_type} = {photons} 光子")

                else:

                    logger.warning(f"⚠️ 扣费失败: {tool_name} ({feature_type}) - {error_msg}")

                    logger.info(f"📝 已记录扣费失败到会话 {conversation_id}: {feature_type} = {photons} 光子 (失败原因: {error_msg})")



            except Exception as e:

                logger.error(f"息记录扣费到会话失息 {e}", exc_info=True)



            return result



        except Exception as e:

            logger.error(f"息扣费异常: {tool_name} ({feature_type}) - {e}", exc_info=True)

            return {

                "success": False,

                "message": f"扣费异常: {str(e)}",

                "photons": 0,

                "feature_type": feature_type

            }



    def _evaluate_billing_need(

        self,

        tool_name: Optional[str],

        result: Any,

        tool_args: Optional[Dict[str, Any]] = None

    ) -> tuple[bool, int]:

        """

        Decide whether to charge and how many units based on tool output.

        Returns: (should_charge, quantity)

        """

        try:

            if not tool_name or not isinstance(result, dict):

                return (False, 0)



            feature_type = TOOL_FEATURE_MAPPING.get(tool_name)

            if not feature_type:

                return (False, 0)



            # Generic failure flag

            if result.get('success') is False:

                return (False, 0)



            # Batch compute tools

            if tool_name in ['calculate_phonon_from_directory', 'calculate_kappa_from_directory', 'batch_calculate_kappa']:

                if isinstance(result.get('completed'), int):

                    qty = max(0, int(result.get('completed') or 0))

                else:

                    items = result.get('results') or []

                    qty = sum(1 for it in items if isinstance(it, dict) and it.get('success'))

                return (qty > 0, qty)



            # Single-run compute/report/analysis

            if feature_type in ['phonon', 'kappa', 'relaxation', 'structure_gen', 'report', 'analysis']:

                if feature_type == 'structure_gen':

                    structs = result.get('structures') or result.get('frontend_structures') or []

                    return (len(structs) > 0, 1 if len(structs) > 0 else 0)

                return (bool(result.get('success')), 1 if result.get('success') else 0)



            # Database/search tools

            if feature_type in ['database', 'search']:

                # Do not charge when explicit error or empty results (unless opted in)

                if result.get('error'):

                    return (False, 0)

                if feature_type == 'search':
                    should_charge = False
                    quantity = 0
                    reason = "no_results"

                    papers = result.get('papers') or result.get('final_papers')
                    if isinstance(papers, list):
                        if len(papers) > 0:
                            should_charge = True
                            quantity = 1
                            reason = "papers_list"
                    else:
                        # Unified search response may not include papers list; rely on counts.
                        total_results = result.get('total_results')
                        if isinstance(total_results, int) and total_results > 0:
                            should_charge = True
                            quantity = 1
                            reason = "total_results"
                        papers_added = result.get('papers_added')
                        if not should_charge and isinstance(papers_added, int) and papers_added > 0:
                            should_charge = True
                            quantity = 1
                            reason = "papers_added"
                        total_papers_in_csv = result.get('total_papers_in_csv')
                        if not should_charge and isinstance(total_papers_in_csv, int) and total_papers_in_csv > 0:
                            should_charge = True
                            quantity = 1
                            reason = "total_papers_in_csv"

                    logger.info(f"[Billing evaluate] feature={feature_type}, should_charge={should_charge}, quantity={quantity}, reason={reason}")
                    return (should_charge, quantity)

                # database
                structures = result.get('structures') or result.get('database_structures') or []
                count = result.get('count')

                from .config import billing_flags as _flags

                if isinstance(structures, list) and len(structures) > 0:
                    logger.info("[Billing evaluate] feature=database, should_charge=True, quantity=1, reason=structures_list")
                    return (True, 1)

                if isinstance(count, int) and count > 0:
                    logger.info("[Billing evaluate] feature=database, should_charge=True, quantity=1, reason=count")
                    return (True, 1)

                if getattr(_flags, 'DB_CHARGE_ON_EMPTY', False):
                    logger.info("[Billing evaluate] feature=database, should_charge=True, quantity=1, reason=charge_on_empty")
                    return (True, 1)

                logger.info("[Billing evaluate] feature=database, should_charge=False, quantity=0, reason=no_results")
                return (False, 0)



            # Default

            return (bool(result.get('success')), 1 if result.get('success') else 0)



        except Exception as e:

            logger.error(f"_evaluate_billing_need error for {tool_name}: {e}")

            return (False, 0)



    async def _handle_agent_event(

        self,

        event: Any,

        agent_id: str,

        websocket: Any,

        client_id: str,

        session_id: Optional[str] = None

    ) -> None:

        """Handle agent event"""

        session_key = f"{client_id}_{agent_id}_{session_id or 'default'}"

        try:
            if self.should_stop(session_key):
                logger.info(f"🛑 Skipping event handling due to stop flag: {session_key}")
                return

            event_type = type(event).__name__

            logger.debug(f"📨 Agent event: {event_type}")

            logger.debug(f"📨 Event attributes: {dir(event)}")



            # 获取计费服务（用于计算消息级别的计费息

            billing_service = get_billing_service()



            # Handle text content

            if hasattr(event, 'content') and event.content:

                content_obj = event.content

                if hasattr(content_obj, 'parts') and content_obj.parts:

                    for part in content_obj.parts:

                        if hasattr(part, 'text') and part.text:

                            text_content = part.text

                            if text_content.strip():

                                # 获取当前会话的tool calls

                                # 使用息process_chat_message() 相同息session_key 格式

                                session_key = f"{client_id}_{agent_id}_{session_id or 'default'}"

                                tool_calls = self.current_tool_calls.get(session_key, [])



                                # 计算本条消息息token 使用增量

                                billing_data = None

                                try:

                                    from services.user_billing_config import get_billing_context_manager

                                    context_manager = get_billing_context_manager()



                                    start_billing_info = self.message_start_billing.get(session_key, {})

                                    conversation_id = start_billing_info.get('conversation_id', session_id or 'unknown')



                                    context = context_manager.get_context(conversation_id)

                                    if context:

                                        current_snapshot = context.get_snapshot()

                                    else:

                                        current_snapshot = {'total_tokens': 0}



                                    logger.debug(f"📊 [消息统计] 调试信息:")

                                    logger.debug(f"  session_key={session_key}")

                                    logger.debug(f"  conversation_id={conversation_id}")

                                    logger.debug(f"  start_billing_info={start_billing_info}")

                                    logger.debug(f"  current_snapshot={current_snapshot}")



                                    current_tokens = current_snapshot.get('total_tokens', 0) - start_billing_info.get('total_tokens', 0)



                                    if current_tokens > 0:

                                        billing_data = {

                                            'tokens': current_tokens,

                                            'model_name': os.getenv('MODEL_USE', 'qwen-plus')

                                        }

                                        logger.info(f"📊 [消息统计] 本条消息 token 使用: {current_tokens} tokens")

                                except Exception as e:

                                    logger.error(f"⚠️ 计算消息统计失败: {e}", exc_info=True)



                                response_agent_id = agent_id
                                response_metadata = None
                                if agent_id != "research_coordinator":
                                    response_agent_id = "research_coordinator"
                                    response_metadata = {"originAgentId": agent_id}

                                await MessageHandler.send_agent_response(
                                    websocket=websocket,
                                    agent_id=response_agent_id,
                                    content=text_content,
                                    metadata=response_metadata,
                                    tool_calls=tool_calls if tool_calls else None,
                                    billing=billing_data
                                )



            # Handle tool calls - Try multiple ways to get tool calls from the event

            tool_calls = None



            # Method 1: Direct attribute access

            if hasattr(event, 'tool_calls') and event.tool_calls:

                tool_calls = event.tool_calls

                logger.info(f"🔧 Found tool_calls via attribute: {len(tool_calls)} calls")



            # Method 2: get_function_calls() method (Google ADK)

            elif hasattr(event, 'get_function_calls'):

                try:

                    function_calls = event.get_function_calls()

                    if function_calls:

                        tool_calls = function_calls

                        logger.info(f"🔧 Found tool_calls via get_function_calls(): {len(tool_calls)} calls")

                except Exception as e:

                    logger.debug(f"get_function_calls() failed: {e}")



            # Process tool calls if found

            if tool_calls:

                for tool_call in tool_calls:

                    logger.info(f"🔧 Tool called: {tool_call}")

                    logger.info(f"🔧 Tool call type: {type(tool_call)}")

                    logger.info(f"🔧 Tool call attributes: {dir(tool_call)}")



                    # Extract tool name

                    tool_name = None

                    if hasattr(tool_call, 'name'):

                        tool_name = tool_call.name

                    elif hasattr(tool_call, 'function') and hasattr(tool_call.function, 'name'):

                        tool_name = tool_call.function.name



                    if tool_name:

                        # 提取工具调用参数

                        tool_input = {}

                        if hasattr(tool_call, 'args'):

                            tool_input = tool_call.args if isinstance(tool_call.args, dict) else {}

                        elif hasattr(tool_call, 'input'):

                            tool_input = tool_call.input if isinstance(tool_call.input, dict) else {}

                        elif hasattr(tool_call, 'function') and hasattr(tool_call.function, 'args'):

                            tool_input = tool_call.function.args if isinstance(tool_call.function.args, dict) else {}

                        skip_session_injection = tool_name in self._SESSION_ID_EXEMPT_TOOLS

                        # Ensure tools use the active session_id to avoid creating a new one.
                        if not skip_session_injection and session_id:
                            if tool_input.get('session_id') not in (None, session_id):
                                logger.warning(
                                    f"?? Overriding tool session_id {tool_input.get('session_id')} -> {session_id} for {tool_name}"
                                )
                            tool_input = {**tool_input, 'session_id': session_id}

                        # Best-effort: inject session_id into the actual tool call args.
                        if not skip_session_injection and session_id:
                            if hasattr(tool_call, 'args') and isinstance(tool_call.args, dict):
                                tool_call.args['session_id'] = session_id
                            elif hasattr(tool_call, 'input') and isinstance(tool_call.input, dict):
                                tool_call.input['session_id'] = session_id
                            elif (
                                hasattr(tool_call, 'function') and
                                hasattr(tool_call.function, 'args') and
                                isinstance(tool_call.function.args, dict)
                            ):
                                tool_call.function.args['session_id'] = session_id


                        # 记录工具调用信息

                        # 使用息process_chat_message() 相同息session_key 格式

                        session_key = f"{client_id}_{agent_id}_{session_id or 'default'}"

                        if session_key not in self.current_tool_calls:

                            self.current_tool_calls[session_key] = []



                        tool_call_record = {

                            "name": tool_name,

                            "input": tool_input,

                            "timestamp": datetime.now().isoformat(),

                            "status": "pending"

                        }

                        self.current_tool_calls[session_key].append(tool_call_record)
                        self.last_tool_call[session_key] = tool_call_record



                        # 🆕 在工具调用前执行扣费

                        try:

                            # 获取用户凭证（从 WebSocket 服务器的客户端会话中获取息

                            user_access_key = None

                            user_client_name = None

                            user_id_for_charge = None



                            try:

                                from .websocket_server import WebSocketServer

                                ws = WebSocketServer.get_instance()

                                if ws and client_id in ws.client_sessions:

                                    client_session = ws.client_sessions[client_id]



                                    # 🔧 修复：从 cookie_credentials 中获取凭息

                                    cookie_creds = client_session.get("cookie_credentials", {})

                                    user_access_key = cookie_creds.get("access_key")

                                    user_client_name = cookie_creds.get("client_name")



                                    # 获取用户 ID

                                    authed_user_id = client_session.get("authenticated_user_id")

                                    user_id_for_charge = str(authed_user_id) if authed_user_id else (session_id or 'unknown')



                                    logger.debug(f"[Billing credentials] access_key={'present' if user_access_key else 'missing'}, client_name={user_client_name}")

                            except Exception as e:

                                logger.debug(f"无法获取用户凭证: {e}")

                                user_id_for_charge = session_id or 'unknown'



                            # 调用扣费方法

                            charge_result = await self._charge_for_tool_if_needed(

                                tool_name=tool_name,

                                session_id=session_id or 'unknown',

                                user_id=user_id_for_charge,

                                user_access_key=user_access_key,

                                user_client_name=user_client_name,

                                tool_args=tool_input

                            )



                            # 记录扣费结果到工具调用记息

                            tool_call_record["charge_result"] = charge_result



                            # 如果扣费失败，记录警告（但不阻止工具执行息

                            if not charge_result.get("success") and charge_result.get("feature_type"):

                                logger.warning(f"⚠️ 工具 {tool_name} 扣费失败，但继续执行: {charge_result.get('message')}")

                                # 可选：发送扣费失败通知到前息

                                await MessageHandler.send_message(websocket, "warning", {

                                    "message": f"Billing failed: {charge_result.get('message')}. Continuing execution.",

                                })



                        except Exception as e:

                            logger.error(f"息工具扣费异常: {tool_name} - {e}", exc_info=True)

                            # 扣费异常不阻止工具执息



                        # 🆕 发送独立的工具执行消息到前息

                        logger.info(f"🔧 发送工具执行消息(pending): {tool_name}")

                        if not self.should_stop(session_key):
                            await MessageHandler.send_message(websocket, "tool_execution", {
                                "agentId": agent_id,
                                "sessionId": session_id,
                                "toolName": tool_name,
                                "input": tool_input,
                                "status": "pending",
                                "timestamp": tool_call_record["timestamp"]
                            })
                        else:
                            logger.info(f"?? Skip tool_execution pending dispatch due to stop flag: {session_key}")



                        # 根据工具名称生成更友好的提示信息

                        tool_message = self._get_tool_friendly_message(tool_name)
                        self._start_task_heartbeat(session_key, websocket, agent_id, session_id)



                        await MessageHandler.send_message(websocket, "status", {

                            "status": "working",

                            "message": tool_message

                        })



                        # 同时发送thinking消息（保留原有逻辑息

                        await MessageHandler.send_agent_thinking(

                            websocket=websocket,

                            agent_id=agent_id,

                            thinking=f"Using tool: {tool_name}"

                        )



            # Handle tool results - THIS IS CRITICAL!

            # Try multiple ways to get tool results from the event

            tool_results = None



            # Method 1: Direct attribute access

            if hasattr(event, 'tool_results') and event.tool_results:

                tool_results = event.tool_results

                logger.info(f"📊 Found tool_results via attribute: {len(tool_results)} results")



            # Method 2: get_function_responses() method

            elif hasattr(event, 'get_function_responses'):

                try:

                    function_responses = event.get_function_responses()

                    if function_responses:

                        tool_results = function_responses

                        logger.info(f"📊 Found tool_results via get_function_responses(): {len(tool_results)} results")

                except Exception as e:

                    logger.debug(f"get_function_responses() failed: {e}")



            # Process tool results if found

            if tool_results:

                if self.should_stop(session_key):
                    logger.info(f"🛑 Skip tool result processing due to stop flag: {session_key}")
                    return

                for tool_result in tool_results:

                    logger.info(f"📊 Tool result received: {type(tool_result)}")

                    logger.info(f"📊 Tool result attributes: {dir(tool_result)}")



                    # Try to extract the actual result data

                    result_data = None



                    # Try different ways to get result data

                    if hasattr(tool_result, 'result'):

                        result_data = tool_result.result

                        logger.info(f"📊 Got result via .result attribute")

                    elif hasattr(tool_result, 'output'):

                        result_data = tool_result.output

                        logger.info(f"📊 Got result via .output attribute")

                    elif hasattr(tool_result, 'content'):

                        result_data = tool_result.content

                        logger.info(f"📊 Got result via .content attribute")

                    elif isinstance(tool_result, dict):

                        result_data = tool_result

                        logger.info(f"📊 Tool result is already a dict")

                    else:

                        # Try to convert to dict

                        if hasattr(tool_result, 'to_dict'):

                            result_data = tool_result.to_dict()

                            logger.info(f"📊 Got result via .to_dict()")

                        elif hasattr(tool_result, '__dict__'):

                            result_data = tool_result.__dict__

                            logger.info(f"📊 Got result via .__dict__")



                    if result_data:

                        logger.info(f"📊 Processing tool result with type: {type(result_data)}")

                        result_data = self._normalize_tool_result_payload(result_data)
                        result_data = self._unwrap_result_payload(result_data)

                        if isinstance(result_data, dict):

                            if result_data.get("should_stop"):
                                self.stop_flags[session_key] = True
                                logger.info(f"🛑 Tool requested stop: {session_key}")

                            logger.info(f"📊 Result keys: {list(result_data.keys())}")



                            # Check if the actual data is in the 'response' field

                            if 'response' in result_data and isinstance(result_data['response'], dict):

                                logger.info(f"📊 Found nested response field, extracting...")

                                actual_result = result_data['response']

                                logger.info(f"📊 Actual result keys: {list(actual_result.keys())}")

                                result_data = actual_result



                            # Check if the actual data is in the 'result' field (can be nested in response or at top level)

                            # This may need to be done multiple times for deeply nested structures

                            max_depth = 5  # Prevent infinite loops

                            depth = 0

                            while 'result' in result_data and depth < max_depth:

                                depth += 1

                                logger.info(f"📊 [Depth {depth}] Found 'result' key, type: {type(result_data['result'])}")

                                result_obj = result_data['result']



                                # Check if it's a dict

                                if isinstance(result_obj, dict):

                                    logger.info(f"📊 [Depth {depth}] Found nested result field (dict), extracting...")

                                    logger.info(f"📊 [Depth {depth}] Result keys: {list(result_obj.keys())}")

                                    result_data = result_obj

                                # Check if it's an MCP CallToolResult object

                                elif hasattr(result_obj, 'structuredContent') or hasattr(result_obj, 'content'):

                                    logger.info(f"📊 [Depth {depth}] Found MCP CallToolResult object")



                                    # Try structuredContent first

                                    if hasattr(result_obj, 'structuredContent'):

                                        structured_content = result_obj.structuredContent

                                        logger.info(f"📊 [Depth {depth}] structuredContent type: {type(structured_content)}")

                                        if isinstance(structured_content, dict):

                                            logger.info(f"📊 [Depth {depth}] structuredContent keys: {list(structured_content.keys())}")

                                            result_data = structured_content

                                            continue

                                        elif structured_content is not None:

                                            logger.warning(f"⚠️ structuredContent is not a dict: {type(structured_content)}")



                                    # Try content field (list of ContentPart)

                                    if hasattr(result_obj, 'content'):

                                        content = result_obj.content

                                        logger.info(f"📊 [Depth {depth}] content type: {type(content)}")



                                        # If content is a list, try to extract text from first item

                                        if isinstance(content, list) and len(content) > 0:

                                            first_item = content[0]

                                            logger.info(f"📊 [Depth {depth}] first content item type: {type(first_item)}")



                                            # Try to get text from TextContent

                                            if hasattr(first_item, 'text'):

                                                import json

                                                try:

                                                    logger.info(f"📊 [Depth {depth}] content.text preview: {first_item.text[:200] if len(first_item.text) > 200 else first_item.text}")

                                                    text_data = json.loads(first_item.text)

                                                    logger.info(f"📊 [Depth {depth}] Parsed JSON from content.text")

                                                    logger.info(f"📊 [Depth {depth}] Parsed data keys: {list(text_data.keys()) if isinstance(text_data, dict) else 'not a dict'}")

                                                    if isinstance(text_data, dict):

                                                        result_data = text_data

                                                        continue

                                                except json.JSONDecodeError as e:
                                                    logger.warning(f"?? content.text is not valid JSON: {e}")
                                                    logger.warning(f"?? content.text value: {first_item.text[:500] if len(first_item.text) > 500 else first_item.text}")
                                                    # Friendly fallback: treat raw text as tool error
                                                    result_data = {
                                                        "status": "error",
                                                        "error": first_item.text,
                                                        "tool_error": True,
                                                        "error_type": "tool_output_non_json"
                                                    }
                                                    break
                                        elif isinstance(content, str):

                                            # Try to parse as JSON

                                            import json

                                            try:

                                                text_data = json.loads(content)

                                                logger.info(f"📊 [Depth {depth}] Parsed JSON from content string")

                                                if isinstance(text_data, dict):

                                                    result_data = text_data

                                                    continue

                                            except json.JSONDecodeError:

                                                logger.warning(f"⚠️ content string is not valid JSON")
                                                # Friendly fallback: treat raw string as tool error
                                                result_data = {
                                                    "status": "error",
                                                    "error": content,
                                                    "tool_error": True,
                                                    "error_type": "tool_output_non_json"
                                                }
                                                break



                                    if not isinstance(result_data, dict):
                                        result_data = {
                                            "status": "error",
                                            "error": "Could not extract structured data from tool result.",
                                            "tool_error": True,
                                            "error_type": "tool_output_unparseable"
                                        }
                                    logger.warning(f"⚠️ Could not extract data from MCP CallToolResult")

                                    break

                                else:

                                    logger.warning(f"⚠️ 'result' is not a dict or MCP object, it's {type(result_obj)}")

                                    logger.warning(f"⚠️ 'result' value: {result_obj}")

                                    break



                            if depth > 0:

                                logger.info(f"📊 息Finished extracting nested results after {depth} levels")

                                logger.info(f"📊 息Final result keys: {list(result_data.keys()) if isinstance(result_data, dict) else 'not a dict'}")



                        pending_record = self._select_pending_tool_record(
                            session_key,
                            tool_result=tool_result,
                            result_data=result_data
                        )
                        pending_tool_name = pending_record.get("name") if pending_record else None
                        nested_tool_name = self._infer_tool_name_from_result(tool_result, result_data)
                        if nested_tool_name and nested_tool_name != pending_tool_name:
                            await MessageHandler.send_message(websocket, "tool_execution", {
                                "agentId": agent_id,
                                "sessionId": session_id,
                                "toolName": nested_tool_name,
                                "output": result_data,
                                "status": "success",
                                "timestamp": datetime.now().isoformat()
                            })
                        if pending_tool_name == "deep_research_agent":
                            await self._maybe_emit_papers_csv_artifacts(
                                websocket=websocket,
                                agent_id=pending_tool_name,
                                session_id=session_id,
                                result_data=result_data
                            )
                            await self._maybe_emit_analysis_artifacts(
                                websocket=websocket,
                                agent_id=pending_tool_name,
                                session_id=session_id,
                                result_data=result_data
                            )
                        if pending_tool_name in {"batch_paper_analysis", "generate_research_report"}:
                            await self._maybe_emit_analysis_artifacts(
                                websocket=websocket,
                                agent_id=agent_id,
                                session_id=session_id,
                                result_data=result_data
                            )

                        self._save_evidence_from_result(agent_id, result_data, session_id)

                        payloads = self._collect_tool_payloads(result_data)
                        if payloads:
                            for payload in payloads:
                                await DataProcessor.process_tool_result(
                                    result=payload,
                                    agent_id=agent_id,
                                    websocket=websocket,
                                    session_id=session_id  # Pass session_id
                                )
                        else:
                            await DataProcessor.process_tool_result(
                                result=result_data,
                                agent_id=agent_id,
                                websocket=websocket,
                                session_id=session_id  # Pass session_id
                            )

                        if pending_tool_name == "database_agent" and not payloads:
                            await self._maybe_emit_database_structures_from_storage(
                                websocket=websocket,
                                agent_id=agent_id,
                                session_id=session_id,
                                result_data=result_data
                            )



                        # 💳 Postpaid billing: charge only after real success

                        try:

                            if billing_flags.POSTPAID_BILLING:

                                # Determine tool name and input of the pending call

                                pending_name = None

                                pending_input = None

                                pending_record = self._select_pending_tool_record(
                                    session_key,
                                    tool_result=tool_result,
                                    result_data=result_data
                                )
                                if pending_record:
                                    pending_name = pending_record.get("name")
                                    pending_input = pending_record.get("input")

                                if not pending_name:

                                    last_call = self.last_tool_call.get(session_key)

                                    if last_call:

                                        pending_name = last_call.get("name")

                                        pending_input = last_call.get("input")



                                should_charge, quantity = self._evaluate_billing_need(pending_name, result_data, pending_input)



                                if should_charge and quantity > 0:

                                    # load user credentials for billing

                                    user_access_key = None

                                    user_client_name = None

                                    user_id_for_charge = None

                                    try:

                                        from .websocket_server import WebSocketServer

                                        ws = WebSocketServer.get_instance()

                                        if ws and client_id in ws.client_sessions:

                                            client_session = ws.client_sessions[client_id]

                                            cookie_creds = client_session.get("cookie_credentials", {})

                                            user_access_key = cookie_creds.get("access_key")

                                            user_client_name = cookie_creds.get("client_name")

                                            authed_user_id = client_session.get("authenticated_user_id")

                                            user_id_for_charge = str(authed_user_id) if authed_user_id else (session_id or 'unknown')

                                    except Exception as e:

                                        logger.debug(f"cannot get user creds (postpaid): {e}")

                                        user_id_for_charge = session_id or 'unknown'



                                    feature_type = TOOL_FEATURE_MAPPING.get(pending_name)

                                    charge_result = PricingService.charge_for_feature(

                                        feature_type=feature_type,

                                        session_id=session_id or 'unknown',

                                        user_id=user_id_for_charge,

                                        user_access_key=user_access_key,

                                        user_client_name=user_client_name,

                                        quantity=quantity

                                    )



                                    # record into billing context

                                    try:

                                        from services.user_billing_config import get_billing_context_manager

                                        context_manager = get_billing_context_manager()

                                        conversation_id = session_id or 'unknown'

                                        context = context_manager.get_or_create_context(

                                            conversation_id=conversation_id,

                                            user_id=user_id_for_charge or 'unknown'

                                        )

                                        photons = charge_result.get("photons", 0)

                                        success = charge_result.get("success", False)

                                        error_msg = charge_result.get("message", "未知错误")

                                        context.record_feature_charge(

                                            feature_type=feature_type,

                                            photons=photons,

                                            success=success,

                                            error_message=None if success else error_msg

                                        )

                                    except Exception as e:

                                        logger.error(f"记录后置扣费失败: {e}", exc_info=True)



                        except Exception as e:

                            logger.error(f"后置扣费流程异常: {e}", exc_info=True)



                        # 更新工具调用记录的输息

                        # 使用息process_chat_message() 相同息session_key 格式

                        session_key = f"{client_id}_{agent_id}_{session_id or 'default'}"

                        tool_name = None

                        tool_input = None

                        tool_timestamp = None



                        pending_record = self._select_pending_tool_record(
                            session_key,
                            tool_result=tool_result,
                            result_data=result_data
                        )

                        status = "success"
                        error_detail = None
                        if isinstance(result_data, dict):
                            if result_data.get("success") is False or result_data.get("error"):
                                status = "error"
                                error_detail = result_data.get("message") or result_data.get("error") or "tool_failed"

                        if pending_record:
                            pending_record["output"] = result_data
                            pending_record["status"] = status
                            if error_detail:
                                pending_record["error"] = error_detail

                            tool_name = pending_record.get("name")
                            tool_input = pending_record.get("input")
                            tool_timestamp = pending_record.get("timestamp")



                        # 🆕 发送工具执行消息到前端

                        if tool_name:

                            logger.info(f"🔧 发送工具执行消息({status}): {tool_name}")

                            if not self.should_stop(session_key):
                                await MessageHandler.send_message(websocket, "tool_execution", {

                                "agentId": agent_id,

                                "sessionId": session_id,

                                "toolName": tool_name,

                                "input": tool_input,

                                "output": result_data,

                                "status": status,

                                "timestamp": tool_timestamp or datetime.now().isoformat()

                            })
                            else:
                                logger.info(f"🔧 Skip tool_execution {status} dispatch due to stop flag: {session_key}")

                        # 清理已完成的工具调用记录，避免影响后续扣费与状态
                        if session_key in self.current_tool_calls:
                            remaining = [
                                record for record in self.current_tool_calls[session_key]
                                if record.get("status") == "pending"
                            ]
                            self.current_tool_calls[session_key] = remaining



                        # 工具结果处理完成后，发送thinking状息

                        await MessageHandler.send_message(websocket, "status", {

                            "status": "thinking",

                            "message": "正在分析工具返回结果..."

                        })

                    else:

                        logger.warning(f"?? Could not extract result data from tool_result: {type(tool_result)}")

                        pending_record = self._select_pending_tool_record(
                            session_key,
                            tool_result=tool_result,
                            result_data=None
                        )
                        if pending_record:
                            pending_record["status"] = "error"
                            pending_record["error"] = "tool_result_missing"
                            tool_name = pending_record.get("name")
                            tool_input = pending_record.get("input")
                            tool_timestamp = pending_record.get("timestamp")

                            if not self.should_stop(session_key):
                                await MessageHandler.send_message(websocket, "tool_execution", {
                                    "agentId": agent_id,
                                    "sessionId": session_id,
                                    "toolName": tool_name,
                                    "input": tool_input,
                                    "status": "error",
                                    "error": "tool_result_missing",
                                    "timestamp": tool_timestamp or datetime.now().isoformat()
                                })

                        if session_key in self.current_tool_calls:
                            remaining = [
                                record for record in self.current_tool_calls[session_key]
                                if record.get("status") == "pending"
                            ]
                            self.current_tool_calls[session_key] = remaining




        except Exception as e:

            logger.error(f"Failed to handle agent event: {e}", exc_info=True)



    def clear_session(self, client_id: str, agent_id: str, session_id: Optional[str] = None):

        """

        Clear session for client and agent



        Args:

            client_id: Client ID

            agent_id: Agent ID

            session_id: Optional session ID

        """

        session_key = f"{client_id}_{agent_id}_{session_id or 'default'}"



        if session_key in self.session_services:

            self._persist_history_for_session_key(session_key, reason="clear_session")

            del self.session_services[session_key]

            del self.runners[session_key]

            del self.adk_sessions[session_key]
            self.session_id_map.pop(session_key, None)

            if session_key in self.session_message_counts:

                del self.session_message_counts[session_key]

            # 🆕 清除停止标志

            self.clear_stop_flag(session_key)

            logger.info(f"🗑息Cleared session: {session_key}")



    def clear_all_sessions(self, client_id: str):

        """

        Clear all sessions for a client



        Args:

            client_id: Client ID

        """

        keys_to_remove = [

            key for key in self.session_services.keys()

            if key.startswith(f"{client_id}_")

        ]



        for key in keys_to_remove:

            self._persist_history_for_session_key(key, reason="client_disconnect")

            del self.session_services[key]

            del self.runners[key]

            del self.adk_sessions[key]
            self.session_id_map.pop(key, None)

            if key in self.session_message_counts:

                del self.session_message_counts[key]

            # 🆕 清除停止标志

            self.clear_stop_flag(key)



        logger.info(f"🗑息Cleared {len(keys_to_remove)} sessions for client {client_id}")



    def get_session_count(self) -> int:

        """Get total number of active sessions"""

        return len(self.session_services)



    def get_client_session_count(self, client_id: str) -> int:

        """Get number of sessions for a specific client"""

        return len([

            key for key in self.session_services.keys()

            if key.startswith(f"{client_id}_")

        ])



    def get_session_info(self, client_id: str, agent_id: str, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:

        """

        Get session information including message count



        Args:

            client_id: Client ID

            agent_id: Agent ID

            session_id: Optional session ID



        Returns:

            Dict with session info or None if session does not exist

        """

        session_key = f"{client_id}_{agent_id}_{session_id or 'default'}"



        if session_key in self.session_services:

            return {

                "session_key": session_key,

                "message_count": self.session_message_counts.get(session_key, 0),

                "max_messages": MAX_CONTEXT_MESSAGES,

                "needs_summary": self.session_message_counts.get(session_key, 0) >= CONTEXT_SUMMARY_THRESHOLD

            }

        return None



    def stop_current_task(self, client_id: str, agent_id: str, session_id: Optional[str] = None):

        """

        🆕 停止当前任务



        Args:

            client_id: Client ID

            agent_id: Agent ID

            session_id: Optional session ID

        """

        session_key = f"{client_id}_{agent_id}_{session_id or 'default'}"

        self.stop_flags[session_key] = True
        self._stop_task_heartbeat(session_key)

        logger.info(f"🛑 设置停止标志: {session_key}")

        # Cancel active task if still running.
        try:
            task = self.active_tasks.get(session_key)

            if task and not task.done():
                task.cancel()
                logger.info(f"Canceled active task: {session_key}")
        except Exception as e:
            logger.warning(f"Failed to cancel active task: {e}")

        self._persist_history_for_session_key(session_key, reason="stop_requested")



    def should_stop(self, session_key: str) -> bool:

        """

        🆕 检查是否应该停息



        Args:

            session_key: Session key



        Returns:

            True if should stop, False otherwise

        """

        return self.stop_flags.get(session_key, False)



    def clear_stop_flag(self, session_key: str):

        """

        🆕 清除停止标志



        Args:

            session_key: Session key

        """

        if session_key in self.stop_flags:

            del self.stop_flags[session_key]

            logger.info(f"息清除停止标志: {session_key}")











