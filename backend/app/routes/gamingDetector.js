function toMinutes(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.getTime() / 60000;
}

function detectPermitGaming(activePermits = []) {
  const permits = Array.isArray(activePermits) ? activePermits : [];

  for (let i = 0; i < permits.length; i += 1) {
    for (let j = i + 1; j < permits.length; j += 1) {
      const first = permits[i];
      const second = permits[j];

      if ((first.zone || '') !== (second.zone || '')) {
        continue;
      }

      const firstStart = toMinutes(first.startTime);
      const firstEnd = toMinutes(first.endTime);
      const secondStart = toMinutes(second.startTime);
      const secondEnd = toMinutes(second.endTime);

      if (firstStart === null || firstEnd === null || secondStart === null || secondEnd === null) {
        continue;
      }

      const overlapStart = Math.max(firstStart, secondStart);
      const overlapEnd = Math.min(firstEnd, secondEnd);
      const overlapMinutes = overlapEnd - overlapStart;

      const withinThirtyMinutes = Math.abs(firstStart - secondStart) <= 30 || Math.abs(firstEnd - secondEnd) <= 30;

      const oneConfinedOneHot =
        ((first.type || '').toLowerCase().includes('confined') && (second.type || '').toLowerCase().includes('hot')) ||
        ((second.type || '').toLowerCase().includes('confined') && (first.type || '').toLowerCase().includes('hot'));

      if (oneConfinedOneHot && (overlapMinutes >= 0 || withinThirtyMinutes)) {
        return {
          suspicious: true,
          reason: `Suspicious permit combination detected in ${first.zone}: ${first.type} and ${second.type} overlap or occur within 30 minutes in the same zone.`,
        };
      }
    }
  }

  return {
    suspicious: false,
    reason: 'No suspicious permit combination detected.',
  };
}

module.exports = {
  detectPermitGaming,
};
