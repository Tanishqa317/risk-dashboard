function getZoneGasPpm(zone = {}) {
  const sensor = zone.gasSensor || {};
  const candidates = [
    sensor.gas_ppm,
    sensor.ppm,
    sensor.co2,
    sensor.methane,
    sensor.h2s,
    sensor.gasPpm,
  ].filter((value) => typeof value === 'number' && Number.isFinite(value));

  if (candidates.length === 0) {
    return 0;
  }

  return Math.max(...candidates);
}

function checkGuardrail(plantState = {}, engineOutput = {}) {
  const zones = Array.isArray(plantState.zones) ? plantState.zones : [];
  const permits = Array.isArray(plantState.activeWorkPermits) ? plantState.activeWorkPermits : [];
  const supervisors = Array.isArray(plantState.supervisors) ? plantState.supervisors : [];

  for (const zone of zones) {
    const zoneId = zone.zoneId;
    const gasPpm = getZoneGasPpm(zone);

    const hotWorkPermit = permits.some((permit) => {
      const permitZone = permit.zone || '';
      const permitType = (permit.type || '').toLowerCase();
      return permitZone === zoneId && permitType.includes('hot');
    });

    if (gasPpm > 500 && hotWorkPermit) {
      return {
        risk_score: 100,
        flagged_zone: zoneId,
        reasoning: `Guardrail rule fired: block hot work when gas_ppm exceeds 500 in ${zoneId}. This overrides the AI decision.`,
        contributing_factors: ['hot-work permit active', 'gas_ppm > 500'],
      };
    }
  }

  const confinedSpacePermit = permits.find((permit) => {
    const permitType = (permit.type || '').toLowerCase();
    return permitType.includes('confined');
  });

  if (confinedSpacePermit) {
    const hasSecondSupervisor = supervisors.filter(Boolean).length >= 2;

    if (!hasSecondSupervisor) {
      return {
        risk_score: 100,
        flagged_zone: confinedSpacePermit.zone || 'unknown',
        reasoning: 'Guardrail rule fired: confined space entry requires a second supervisor. This overrides the AI decision.',
        contributing_factors: ['confined-space permit active', 'missing second supervisor'],
      };
    }
  }

  return {
    ...engineOutput,
    reasoning: engineOutput.reasoning || 'No guardrail violation detected.',
  };
}

module.exports = {
  checkGuardrail,
};
