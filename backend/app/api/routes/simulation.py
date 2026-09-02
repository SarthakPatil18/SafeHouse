"""Simulation playback API route to test ESP32 rover scenarios in real-time."""

import asyncio
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, Query
from pydantic import BaseModel

from app.core.logging import logger
from app.robotics.state_machine import RobotState
from app.schemas.responses import ErrorDetail, ErrorResponse, SuccessResponse
from app.schemas.sensors import SensorReadingCreate
from app.services.robot_service import get_state_machine
from app.services.sensor_service import SensorService
from simulation.fake_esp32 import SCENARIO_SCRIPTS, run_scenario_async

router = APIRouter(prefix="/simulation", tags=["Simulation"])

# Active background simulation task reference
_current_sim_task: Optional[asyncio.Task] = None
_sim_state: Dict[str, Any] = {
    "is_running": False,
    "active_scenario": None,
    "step_count": 0,
}


async def _playback_scenario_task(scenario_name: str, delay_seconds: float = 1.5) -> None:
    """Async background task that streams scenario readings into SensorService."""
    global _sim_state
    _sim_state["is_running"] = True
    _sim_state["active_scenario"] = scenario_name
    _sim_state["step_count"] = 0

    sm = get_state_machine()
    if scenario_name == "device_offline":
        sm.set_offline()
    else:
        sm.set_online()

    try:
        async for reading_dict in run_scenario_async(scenario_name, delay_seconds=delay_seconds):
            if not _sim_state["is_running"]:
                break

            _sim_state["step_count"] += 1
            if scenario_name == "sensor_failure" and reading_dict.get("gas_mq135") is None:
                # Sensor error logged, skip normal sensor insert
                continue


            reading_in = SensorReadingCreate(**reading_dict)
            await SensorService.record_reading(reading_in, process_worker=True)

    except asyncio.CancelledError:
        logger.info("Simulation playback cancelled.")
    except Exception as e:
        logger.error("Simulation error during %s: %s", scenario_name, e)
    finally:
        _sim_state["is_running"] = False
        _sim_state["active_scenario"] = None


@router.get("/scenarios", response_model=SuccessResponse[List[str]])
async def list_scenarios():
    """List all available scripted simulation scenarios."""
    return SuccessResponse(data=list(SCENARIO_SCRIPTS.keys()))


@router.get("/status", response_model=SuccessResponse[Dict[str, Any]])
async def get_simulation_status():
    """Get active simulation status and progress."""
    return SuccessResponse(data=_sim_state)


@router.post("/start", response_model=SuccessResponse[Dict[str, Any]])
async def start_simulation(
    scenario: str = Query("normal", description="Scenario name to replay"),
    delay: float = Query(1.2, description="Delay in seconds between simulated frames"),
):
    """Start replaying a scripted hardware scenario."""
    global _current_sim_task
    if scenario not in SCENARIO_SCRIPTS:
        return ErrorResponse(
            error=ErrorDetail(
                code="UNKNOWN_SCENARIO",
                message=f"Scenario '{scenario}' not found. Choose from {list(SCENARIO_SCRIPTS.keys())}",
            )
        )

    # Cancel previous simulation if running
    if _current_sim_task and not _current_sim_task.done():
        _current_sim_task.cancel()

    _current_sim_task = asyncio.create_task(
        _playback_scenario_task(scenario_name=scenario, delay_seconds=delay)
    )

    return SuccessResponse(
        data={
            "started": True,
            "scenario": scenario,
            "delay_seconds": delay,
            "message": f"Simulation scenario '{scenario}' started in background.",
        }
    )


@router.post("/stop", response_model=SuccessResponse[Dict[str, Any]])
async def stop_simulation():
    """Stop active simulation playback."""
    global _current_sim_task, _sim_state
    if _current_sim_task and not _current_sim_task.done():
        _current_sim_task.cancel()

    _sim_state["is_running"] = False
    _sim_state["active_scenario"] = None

    return SuccessResponse(data={"stopped": True, "message": "Simulation stopped."})
