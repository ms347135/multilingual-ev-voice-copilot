from __future__ import annotations

from config import DATA_DIR, load_json


def load_vehicle_profiles() -> list[dict]:
    return load_json(DATA_DIR / "vehicle_profiles.json")


def load_vehicle_state(profile_name: str) -> dict:
    states = load_json(DATA_DIR / "mock_vehicle_state.json")
    return states.get(profile_name, {})


def summarize_vehicle_state(state: dict) -> str:
    if not state:
        return "No live vehicle state is available."

    tire_values = state.get("tire_pressure_kpa", {})
    tire_summary = ", ".join(f"{key}: {value} kPa" for key, value in tire_values.items())
    codes = ", ".join(state.get("last_fault_codes", [])) or "none"
    return (
        f"SOC: {state.get('soc')}%. "
        f"Estimated range: {state.get('estimated_range_km')} km. "
        f"Outside temperature: {state.get('outside_temperature_c')} C. "
        f"Battery temperature: {state.get('battery_temperature_c')} C. "
        f"Charging status: {state.get('charging_status')}. "
        f"Plug connected: {state.get('plug_connected')}. "
        f"Cabin AC on: {state.get('cabin_ac_on')}. "
        f"Tire pressure: {tire_summary}. "
        f"Door status: {state.get('door_status')}. "
        f"Fault codes: {codes}."
    )


def get_warning_flags(state: dict) -> list[str]:
    flags: list[str] = []
    if not state:
        return flags

    if state.get("battery_temperature_c", 0) >= 42:
        flags.append("Battery temperature is elevated.")
    if state.get("charging_status") == "interrupted":
        flags.append("Charging is currently interrupted.")
    if any(value < 235 for value in state.get("tire_pressure_kpa", {}).values()):
        flags.append("At least one tire pressure reading is below the recommended range.")
    if state.get("last_fault_codes"):
        flags.append(f"Active fault codes: {', '.join(state['last_fault_codes'])}")
    return flags


def should_use_vehicle_state(query: str, intent: str) -> bool:
    lowered = query.lower()
    keywords = ["range", "soc", "battery", "charging", "tire", "hvac", "air conditioning", "warning", "续航", "电池", "充电", "胎压", "空调"]
    return intent in {"charging_help", "range_question", "warning_light", "troubleshooting"} or any(keyword in lowered for keyword in keywords)
