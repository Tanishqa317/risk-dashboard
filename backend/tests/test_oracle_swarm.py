from app.routes.Oracle import runOracleSwarm


def test_run_oracle_swarm_returns_results_for_all_agents(monkeypatch):
    def fake_call(plant_state, agent_name, system_instruction):
        return {
            "risk_score": {"Aggressive": 90, "Conservative": 40, "Adversarial": 75}[agent_name],
            "flagged_zone": "zone-1",
            "reasoning": f"{agent_name} evaluated the plant state",
        }

    monkeypatch.setattr("app.routes.Oracle._call_oracle_agent", fake_call)

    plant_state = {"zones": [{"zoneId": "zone-1", "gas_ppm": 450}]}
    results = runOracleSwarm(plant_state)

    assert [item["agent"] for item in results] == ["Aggressive", "Conservative", "Adversarial"]
    assert results[0]["risk_score"] == 90
    assert results[1]["risk_score"] == 40
    assert results[2]["risk_score"] == 75
    assert all("reasoning" in item for item in results)
