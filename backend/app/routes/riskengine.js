const GEMINI_API_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent';

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

function fallbackRuleBasedAssessment(plantState = {}) {
  const zones = Array.isArray(plantState.zones) ? plantState.zones : [];
  const permits = Array.isArray(plantState.activeWorkPermits) ? plantState.activeWorkPermits : [];

  for (const zone of zones) {
    const gasPpm = getZoneGasPpm(zone);
    const hasHotWorkPermit = permits.some((permit) => {
      const permitZone = permit.zone || '';
      const permitType = (permit.type || '').toLowerCase();
      return permitZone === zone.zoneId && permitType.includes('hot');
    });

    if (gasPpm > 300 && hasHotWorkPermit) {
      return {
        risk_score: 85,
        flagged_zone: zone.zoneId,
        reasoning: `High risk: gas_ppm ${gasPpm} exceeds 300 ppm while a hot-work permit is active in ${zone.zoneId}.`,
        contributing_factors: ['gas_ppm > 300', 'hot-work permit active in the same zone'],
      };
    }
  }

  const fallbackZone = zones[0]?.zoneId || 'unknown';
  return {
    risk_score: 0,
    flagged_zone: fallbackZone,
    reasoning: 'No fallback rule triggered.',
    contributing_factors: ['no elevated gas and no hot-work overlap'],
  };
}

function normalizeGeminiResult(result = {}) {
  const riskScore = Number(result.risk_score || 0);
  const flaggedZone = result.flagged_zone || 'unknown';
  const reasoning = result.reasoning || 'No reasoning provided.';
  const contributingFactors = Array.isArray(result.contributing_factors)
    ? result.contributing_factors
    : [result.contributing_factors || 'No contributing factors provided.'];

  return {
    risk_score: Number.isFinite(riskScore) ? riskScore : 0,
    flagged_zone: flaggedZone,
    reasoning,
    contributing_factors: contributingFactors,
  };
}

async function assessRisk(plantState = {}, options = {}) {
  const apiKey = options.apiKey || process.env.GEMINI_API_KEY;

  if (!apiKey) {
    return fallbackRuleBasedAssessment(plantState);
  }

  try {
    const response = await fetch(`${GEMINI_API_URL}?key=${apiKey}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contents: [
          {
            role: 'user',
            parts: [
              {
                text: `Analyze this industrial plant safety state and return valid JSON only with this shape: {"risk_score": number, "flagged_zone": string, "reasoning": string, "contributing_factors": string[]}. Plant state: ${JSON.stringify(plantState)}`,
              },
            ],
          },
        ],
      }),
    });

    if (!response.ok) {
      throw new Error(`Gemini API request failed with status ${response.status}`);
    }

    const data = await response.json();
    const aiText = data?.candidates?.[0]?.content?.parts?.[0]?.text || '{}';
    const cleanedText = aiText.match(/\{[\s\S]*\}/)?.[0] || '{}';
    const parsed = JSON.parse(cleanedText);

    return normalizeGeminiResult(parsed);
  } catch (error) {
    return fallbackRuleBasedAssessment(plantState);
  }
}

module.exports = {
  assessRisk,
  fallbackRuleBasedAssessment,
};
