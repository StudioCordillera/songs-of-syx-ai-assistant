# Stored settlement weather candidate

The original code under `dev/candidates/weather/` remains an **unregistered developer candidate**. A separate production implementation is now shipped under map /weather; see [current weather fields](WEATHER.md) and WEATHER_VALIDATION.json. The candidate reports below retain their original source/JAR/date scope. The paired review targets Songs of Syx **0.71.44** and distinguishes documented script lifecycle contracts from shipped-source/selected-bytecode verification of public weather members. No stable official weather API contract is established.

`dev/candidates/weather/syx/assistant/candidate/WeatherObservation.java` copies ten fixed factors and four flags into detached maps, only when a completed instantiated campaign city exists. The caller must use `GAME.addAfterUpdate`. Underlying city weather can remain available with the world view open; the DTO is not a world-region weather map. The later scene follow-up below validates generated battlefield/setup refusal and city reload. Standalone main-menu/unload and all-state coverage remain unestablished. Failure returns unavailable/null; nonfinite or out-of-range factors are refused rather than converted to zero.

| Candidate factor | Public component | Meaning and boundary |
| --- | --- | --- |
| `precipitation_history` | `SWEATHER.moisture.getD()` | Stored rain/thaw history factor; neither current rainfall nor tile ground moisture. The source uses values below 0.25 for drought-related behavior. |
| `ground_snow` | `snow.getD()` | Global stored snow accumulation factor; not a per-tile depth map. |
| `water_ice` | `ice.getD()` | Global stored water-ice factor; not individual tile passability or usable water access. |
| `wind_strength` | `wind.getD()` | Stored game wind strength; no physical speed units, target or forecast. |
| `temperature_scale` | `temp.getD()` | Stored game temperature scale; not Celsius/Fahrenheit or a future target. |
| `cloud_amount` | `clouds.getD()` | Stored game cloud factor; not local cloud geometry or precipitation probability. |
| `downfall_intensity` | `rain.getD()` | Current stored downfall factor, distinct from precipitation history and precipitation type. |
| `thunder_amount` | `thunder.getD()` | Stored thunder factor; not a particular flash, sound or predicted event. |
| `plant_growth` | `growth.getD()` | Global stored plant-growth factor; not a crop-room yield or complete productivity modifier. |
| `seasonal_ripeness` | `growthRipe.getD()` | Global stored seasonal factor; not a particular crop's harvestable inventory. |

Values are finite game-scale factors in [0,1]. `WeatherThing.getD()` reads a stored double. Ordinary setters clamp, but save loading restores the raw value without validation; the candidate therefore checks its own numeric boundary. Ten concrete component classes are final and inherit this getter in the paired binary. No weather setter/update/target function, renderer, light/audio handle, mutable collection, private runtime access or arbitrary member invocation is exposed.

The four flags are `downfall_is_snow` (`snow.rainIsSnow()`), `growth_autumn` (`growth.isAutumn()`), `crops_ripe` (`growthRipe.cropsAreRipe()`) and `ripening` (`growthRipe.ripening()`). They read stored booleans or the sign of stored snow history. They are not UI visibility/selection or forecasts. The engine computes some ripeness flags using the previous factor value before storing its new seasonal factor, so a client must preserve the flags rather than recompute them from simultaneously exported factors. Exact flag/factor age remains unknown. A dry-weather flag is not invented from a room's irrigation or output.

## Evidence

[WEATHER_CANDIDATE_REVIEW.json](WEATHER_CANDIDATE_REVIEW.json) pins source hashes, public declaration anchors and selected accessor disassembly fingerprints. The six selected accessor bodies have no calls, writes, allocation or backward branches. External compilation succeeds. Three accepted/58 rejected detached shape/numeric cases run without initializing a game. Those corruption cases are not native fault injection.

[WEATHER_CANDIDATE_NATIVE_VALIDATION.json](WEATHER_CANDIDATE_NATIVE_VALIDATION.json) separately pins 48 actual after-update samples: sixteen paused-city, sixteen naturally running-city and sixteen paused-world observations, with 672 repeated public getter comparisons. Time advances in the running window and stays fixed in the paused windows; three factors naturally change in that finite window. Direct getter comparisons share engine storage and do not establish independent physical truth.

After excluding the first sample, 47 candidate-collection intervals have median 0.069129 ms/max 0.102327 ms. They include detached maps, numeric checks and tick/time metadata, excluding JSON encoding and independent baseline reads. Maximum candidate JSON is 745 bytes. These local descriptive samples do not establish large-city/FPS/worst-case acceptance. Native guards confirm zero exit, explicit clean completion, absence of known failure markers, copied-mod restoration and copied-save integrity. Public test-only speed/view controls restore pause/city view before exit; simulation progress is discarded without saving.

## Reproduce

Use the licensed paired game/source, full JDK, compatible game Java and validated copied save/profile described in CONTRIBUTING.md. No provider credential is needed.

```sh
.venv/bin/python dev/review_weather_candidate.py \
  --game-dir '/path/to/Songs of Syx' --jdk-home '/path/to/full-jdk' \
  --output WEATHER_CANDIDATE_REVIEW.json
xvfb-run -a -s '-screen 0 1280x960x24' .venv/bin/python dev/run_weather_candidate.py \
  --game-dir '/path/to/Songs of Syx' --jdk-home '/path/to/full-jdk' \
  --java '/path/to/game-compatible/java' --save runtime/smoke.save
```

The native wrapper validates the current candidate/static-review source hashes and exact game pairing, and owns the shared device fixture lock. It reuses the explicit `StockpileScenario` override/ready-file hooks in the existing disposable-game host; those legacy filenames do not reinterpret a stockpile report or replace a production stockpile reader. The shared host now accepts an optional selected boundary review and explicit clean-completion marker; its normal stockpile default remains unchanged. Private actual weather values stay under ignored runtime/.

The original promotion plan required DTO/definitions/discovery, actual lifecycle/refusal, same-observation MCP and paired release checks. The later production checkpoint in WEATHER.md records completed named gates; standalone unload and native malformed-reader behavior remain open. Keep physical units, exact age, regional weather and crop-yield/forecast exclusions. No external weather/guide source is added or refreshed by this work; the existing thirteen-source reference corpus retains its own review dates. The full game-variable/lifecycle/reference objective remains open.


## Actual scene and public-input normalization follow-up

[WEATHER_SCENE_VALIDATION.json](WEATHER_SCENE_VALIDATION.json) separately checks the unchanged candidate in eight actual existing fixture phases: city, city tactical view, city return, generated battle deployment/menu, copied-city reload, initial world setup and terrain setup. Four city phases produce 56 direct getter comparisons with same-callback tick metadata; battle/setup phases return unavailable/null instead of default weather values. The existing production MCP scene suite independently checks current context, session rotation and other entity/tile/regional/warehouse tables. It does not expose candidate weather through MCP or turn a cached snapshot into the candidate's observation.

Seven public inherited wind-setter controls cover NaN, negative/positive infinity, below/above-range and explicit zero/one inputs. The engine's `CLAMP.d` turns these inputs into valid zero/one values. The candidate correctly retains available zero/one, with all unrelated factors/flags unchanged; each control restores the prior wind value bit-exactly in a same-callback `finally`. These are test-only mutations in the disposable profile. No setter is called by the candidate collector or production bridge.

The initial attempted NaN fault fixture was rejected because its assumption was wrong: the public setter does not produce a nonfinite stored getter. A second interrupted attempt completed its scene checks but failed while hashing a nonexistent source filename; final source-path preflight corrects that reporting bug. Neither interrupted attempt is accepted evidence. Actual native nonfinite/out-of-range stored-value refusal, getter exceptions and corrupt saves remain unvalidated; the earlier 58 detached rejection cases keep their narrower scope. No private access or alternate injection mechanism was introduced to force the branch.

`dev/run_weather_scenes.py` / `dev/candidates/weather/scenes/StockpileScenario.java` reuse the locked disposable host. `SceneScenario.install` now has an optional test-only observer that runs in its public after-update callbacks across actual reload/setup and just before clean completion. The original two-argument fixture keeps a null observer. The host passes its already validated copied-save path through a fixed Java property; the candidate validates it again. Reproduce with the native command above replacing `dev/run_weather_candidate.py` with `dev/run_weather_scenes.py`. No provider key is used.

Explicit clean completion, known crash-marker checks, copied-mod restoration and supplied copied-save integrity are required. Battle generation writes only its own disposable fixture saves. The player payload and collector were unchanged at that developer-only checkpoint. Subsequent production integration and paired release gates are recorded in WEATHER.md / WEATHER_VALIDATION.json. Natural battle conclusion, standalone menu/unload, broader climates/seasons, native malformed readers and full UI hierarchy remain open.
