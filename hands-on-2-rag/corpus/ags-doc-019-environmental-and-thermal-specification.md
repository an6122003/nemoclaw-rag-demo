# Environmental and Thermal Specification

**Document ID:** AGS-DOC-019
**Revision:** C
**Effective date:** 2025-07-01
**Applies to:** AX-400, AX-600, Helios H3, Comet C2

## 1. Operating envelopes

| Product | Operating temperature | Thermal derate begins | Storage temperature | Ingress |
|---|---|---|---|---|
| AX-400 (AGS-AX400-372) | -20 °C to +50 °C | Above +40 °C | -30 °C to +60 °C | IP54 |
| AX-600 (AGS-AX600-558) | -25 °C to +50 °C | Above +45 °C | -30 °C to +60 °C | IP55 |
| Helios H3 (AGS-H3-250) | -30 °C to +55 °C | Above +50 °C | -40 °C to +70 °C | IP66 |
| Comet C2 (AGS-C2-SC) | -20 °C to +60 °C | None | -40 °C to +70 °C | IP40 |

The AX-400 and AX-600 differ in both the cold limit and the derate threshold. Do not apply the AX-600 threshold of +45 °C to an AX-400; the AX-400 derate begins at +40 °C.

## 2. Humidity, altitude and seismic

All products operate at 5% to 95% relative humidity, non-condensing. All products operate at up to 2,000 m altitude without derate; above 2,000 m, apply a 1.5% per 100 m current derate. Equipment is qualified to IEEE 693 at a moderate seismic level and is suitable for IBC 2021 sites with a short-period spectral acceleration up to Sds 1.0.

## 3. AX-400 thermal derate

The AX-400 is air cooled by four axial fans. Above +40 °C intake temperature the maximum charge and discharge power must be reduced as specified in safety bulletin SB-2025-04 (AGS-DOC-011): 60% charge and 70% discharge between +40 °C and +45 °C, and 50% charge and 60% discharge between +45 °C and +50 °C. Above +50 °C charge and discharge are inhibited.

## 4. AX-600 thermal derate

The AX-600 is liquid cooled with a 38 L fill of 50% propylene glycol / 50% water at 2.5 bar nominal pressure.

| Intake ambient | Maximum charge power | Maximum discharge power |
|---|---|---|
| At or below +45 °C | 279 kW (100%) | 279 kW (100%) |
| Above +45 °C to +50 °C | 195 kW (70%) | 195 kW (70%) |
| Above +50 °C | Inhibited | Inhibited |

The lower derate threshold on the AX-400 reflects its air-cooled architecture: the AX-600 rejects heat to a liquid loop and therefore tolerates a higher intake temperature before derating.

## 5. Cold-weather behaviour

Below -25 °C the AX-600 inhibits charging until the cells warm above -5 °C; the cabinet heater draws 1.2 kW during warm-up. The AX-400 is rated only to -20 °C and will report F-0101 if energised below that limit. Neither cabinet permits charging below 0 °C.

## 6. Acoustic noise

| Product | Sound pressure at 1 m |
|---|---|
| AX-400 | 62 dBA |
| AX-600 | 58 dBA |
| Helios H3 | 66 dBA |

AX-600 is quieter than AX-400 because it has no cooling fans. Sites with a noise limit below 65 dBA at the property line should account for the Helios H3 as the dominant source.

## 7. Condensation and corrosion

All cabinets are rated for indoor or outdoor installation in a C3 corrosion environment per ISO 12944. For C4 or C5 environments, order the coastal finish option. Do not install any cabinet in a location subject to direct salt spray without the coastal finish.
