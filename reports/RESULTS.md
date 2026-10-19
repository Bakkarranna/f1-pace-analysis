# Race pace, stint and tyre-age analysis

Formula 1, 4 Grands Prix, 4257 clean racing laps. Generated 2026-10-19 22:10 UTC.

This report answers three questions with the measured lap data:

1. **Which driver had the strongest pace over a stint?**
2. **How does lap time change as tyre age increases?**
3. **How does pace change before and after a pit stop?**


## Bahrain

**1062 clean laps, 20 drivers, 4 stints analysed.**

### Strongest pace over a stint

| Driver | Tyre | Clean laps | Median lap (s) | Best 3-lap mean (s) | vs own stint |
|---|---|---|---|---|---|
| 1 | SOFT | 19 | 94.667 | 92.608 | 97.83% |
| 16 | HARD | 22 | 95.206 | 94.090 | 98.83% |
| 11 | SOFT | 20 | 94.864 | 94.430 | 99.54% |
| 4 | HARD | 23 | 95.485 | 94.476 | 98.94% |
| 14 | HARD | 15 | 95.014 | 94.482 | 99.44% |

*Best 3-lap mean* is the trailing 3-lap rolling average, which is how a stint is judged on the pit wall: one fast lap can be a tow or a fuel effect, three in a row is pace. *vs own stint* expresses that as a percentage of the driver's own stint median, so stints from different cars are comparable.

### Tyre degradation

| Compound | Laps | s per lap of tyre age | 95% CI | R-squared |
|---|---|---|---|---|
| Soft | 308 | 0.1084 | 0.0823 to 0.1346 | 0.669 |
| Hard | 754 | 0.1252 | 0.1132 to 0.1371 | 0.468 |

The fuel term is fitted alongside tyre age: a car gets lighter through the race and therefore faster, which would otherwise mask some of the tyre degradation.


## Monaco

**1156 clean laps, 16 drivers, 3 stints analysed.**

### Strongest pace over a stint

| Driver | Tyre | Clean laps | Median lap (s) | Best 3-lap mean (s) | vs own stint |
|---|---|---|---|---|---|
| 1 | HARD | 25 | 75.543 | 74.852 | 99.08% |
| 44 | HARD | 26 | 75.641 | 74.951 | 99.09% |
| 22 | HARD | 73 | 80.135 | 74.972 | 93.56% |
| 63 | MEDIUM | 72 | 78.526 | 75.376 | 95.99% |
| 16 | HARD | 74 | 78.483 | 75.492 | 96.19% |

*Best 3-lap mean* is the trailing 3-lap rolling average, which is how a stint is judged on the pit wall: one fast lap can be a tow or a fuel effect, three in a row is pace. *vs own stint* expresses that as a percentage of the driver's own stint median, so stints from different cars are comparable.

### Tyre degradation

| Compound | Laps | s per lap of tyre age | 95% CI | R-squared |
|---|---|---|---|---|
| Medium | 374 | 0.0128 | 0.0023 to 0.0233 | 0.571 |
| Hard | 750 | 0.0389 | 0.0312 to 0.0465 | 0.543 |
| Soft | 32 | 0.0449 | -0.0340 to 0.1237 | 0.046 |

The fuel term is fitted alongside tyre age: a car gets lighter through the race and therefore faster, which would otherwise mask some of the tyre degradation.


## Monza

**931 clean laps, 20 drivers, 3 stints analysed.**

### Strongest pace over a stint

| Driver | Tyre | Clean laps | Median lap (s) | Best 3-lap mean (s) | vs own stint |
|---|---|---|---|---|---|
| 1 | MEDIUM | 11 | 82.585 | 81.745 | 98.98% |
| 4 | HARD | 20 | 82.557 | 82.001 | 99.33% |
| 81 | HARD | 14 | 82.377 | 82.105 | 99.67% |
| 63 | HARD | 19 | 82.799 | 82.119 | 99.18% |
| 44 | HARD | 15 | 82.471 | 82.206 | 99.68% |

*Best 3-lap mean* is the trailing 3-lap rolling average, which is how a stint is judged on the pit wall: one fast lap can be a tow or a fuel effect, three in a row is pace. *vs own stint* expresses that as a percentage of the driver's own stint median, so stints from different cars are comparable.

### Tyre degradation

| Compound | Laps | s per lap of tyre age | 95% CI | R-squared |
|---|---|---|---|---|
| Medium | 240 | 0.0272 | -0.0011 to 0.0555 | 0.409 |
| Hard | 690 | 0.0799 | 0.0706 to 0.0891 | 0.498 |

The fuel term is fitted alongside tyre age: a car gets lighter through the race and therefore faster, which would otherwise mask some of the tyre degradation.


## Singapore

**1108 clean laps, 20 drivers, 3 stints analysed.**

### Strongest pace over a stint

| Driver | Tyre | Clean laps | Median lap (s) | Best 3-lap mean (s) | vs own stint |
|---|---|---|---|---|---|
| 20 | SOFT | 6 | 98.112 | 94.754 | 96.58% |
| 16 | HARD | 25 | 96.454 | 95.575 | 99.09% |
| 4 | HARD | 31 | 96.631 | 95.765 | 99.10% |
| 81 | HARD | 23 | 96.610 | 95.985 | 99.35% |
| 1 | HARD | 32 | 96.786 | 96.108 | 99.30% |

*Best 3-lap mean* is the trailing 3-lap rolling average, which is how a stint is judged on the pit wall: one fast lap can be a tow or a fuel effect, three in a row is pace. *vs own stint* expresses that as a percentage of the driver's own stint median, so stints from different cars are comparable.

### Tyre degradation

| Compound | Laps | s per lap of tyre age | 95% CI | R-squared |
|---|---|---|---|---|
| Soft | 91 | 0.0086 | -0.0229 to 0.0401 | 0.229 |
| Medium | 505 | 0.0354 | 0.0243 to 0.0464 | 0.075 |
| Hard | 512 | 0.0905 | 0.0814 to 0.0995 | 0.601 |

The fuel term is fitted alongside tyre age: a car gets lighter through the race and therefore faster, which would otherwise mask some of the tyre degradation.


## Degradation across races

| Race | Compound | Laps | s per lap of tyre age | 95% CI |
|---|---|---|---|---|
| bahrain | Soft | 308 | 0.1084 | 0.0823 to 0.1346 |
| bahrain | Hard | 754 | 0.1252 | 0.1132 to 0.1371 |
| monaco | Medium | 374 | 0.0128 | 0.0023 to 0.0233 |
| monaco | Hard | 750 | 0.0389 | 0.0312 to 0.0465 |
| monaco | Soft | 32 | 0.0449 | -0.0340 to 0.1237 |
| monza | Medium | 240 | 0.0272 | -0.0011 to 0.0555 |
| monza | Hard | 690 | 0.0799 | 0.0706 to 0.0891 |
| singapore | Soft | 91 | 0.0086 | -0.0229 to 0.0401 |
| singapore | Medium | 505 | 0.0354 | 0.0243 to 0.0464 |
| singapore | Hard | 512 | 0.0905 | 0.0814 to 0.0995 |