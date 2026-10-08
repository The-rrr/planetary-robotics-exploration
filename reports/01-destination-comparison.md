# The Moon, Mars and Europa as Exploration Destinations

**Study report, consolidated 9 October 2026 from earlier exploration notes.** This comparison motivates the navigation project. It is a qualitative learning exercise, not a mission feasibility study or a numerical ranking.

## Comparing scientific questions and engineering needs

| Destination | Scientific motivation | Relevant environmental constraints | Implications for exploration robots |
|---|---|---|---|
| Moon | Surface geology, volatile resources and a record of Solar System history | Vacuum, dust, rough terrain and strong illumination differences; polar shadow introduces an especially demanding case | Terrain mapping, safe local navigation and perception that handles difficult lighting |
| Mars | Geological and climate history, past habitable environments and preserved evidence in rocks | Thin atmosphere, dust, loose regolith, slopes and delayed interaction with Earth | Onboard navigation, slip-aware odometry, obstacle detection and links between traversability and scientific targets |
| Europa | Investigating the potential habitability of an ocean beneath the ice shell | Icy terrain, Jupiter's radiation environment, difficult access to the ocean and major uncertainty about conditions below the ice | Separate surface exploration from hypothetical ocean exploration; justify sensors, communications and autonomy for each environment |

The planetary background comes from NASA's [Moon](https://science.nasa.gov/moon/), [Mars](https://science.nasa.gov/mars/) and [Europa](https://science.nasa.gov/jupiter/jupiter-moons/europa/) summaries. The navigation implications in the final column are my engineering interpretation of those constraints.

## What existing mission approaches teach me

For the Moon, mapping and local observations help connect scientific questions with landing and surface-operation requirements. Mars exploration shows the value of connecting orbital context with local rover measurements: the rover must both reach a target and understand whether the route is safe. NASA's [Mars exploration programme](https://science.nasa.gov/planetary-science/programs/mars-exploration/) provides the broader mission context.

For Europa, the immediate scientific question is habitability. [Europa Clipper](https://science.nasa.gov/mission/europa-clipper/) investigates Europa through a Jupiter-orbiting spacecraft and close flybys; it is not an underwater robot. [ESA's Juice](https://www.esa.int/Science_Exploration/Space_Science/Juice) provides a comparative investigation of Jupiter's icy moons. These approaches highlight how remote observations must constrain environmental assumptions before an ambitious future in-situ architecture can be justified.

Evidence for an ocean or a potentially habitable environment is not evidence that life has been found. I also distinguish possible future ice-penetrating or ocean robots from the missions actually described in the source material.

## How the comparison shaped the practical project

The common thread is navigation under unfamiliar conditions, with limited access to external position references and imperfect sensor information. Europa particularly encouraged me to think about environment-dependent sensing and reliable autonomy. To build a foundation, I began with an accessible indoor RGB-D dataset and a conventional SLAM stack.

The indoor experiment answers a narrower question: can I correctly process depth, associate frames, reconstruct geometry, estimate motion and verify loop closures? It does not yet test icy terrain, vacuum, radiation, underwater sensing or interplanetary communication. My next step is to introduce controlled visual degradation in a terrestrial benchmark or explicitly labelled analogue simulation before making broader claims.

## Questions for further work

- How should a robot balance safe travel with access to scientifically valuable targets?
- What happens when texture, illumination or depth measurements become unreliable?
- Which parts of a navigation method transfer between environments, and which require different sensor models?
- Could multiple robots share compact information to improve coverage and resilience without depending on continuous communication?

These questions lead to [the cooperative exploration concept](02-cooperative-exploration-concept.md) and [the recorded SLAM experiment](03-slam-experiment.md).
