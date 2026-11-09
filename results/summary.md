## Apple M5 Max

| Model | Dataset | Strict recall | Char. precision | Size (MB) | p95 latency (ms) |
|---|---|---|---|---|---|
| gliner2 | t1-open-pii-500k | 81.8 % | 96.7 % | 1244.4 |  |
| gliner2 | t1-openpii-1m | 80.7 % | 98.2 % | 1244.4 |  |
| gliner2 | t1-swiss | 78.2 % | 89.6 % | 1244.4 |  |
| presidio | t1-open-pii-500k | 63.5 % | 89.0 % | 2357.4 |  |
| presidio | t1-openpii-1m | 54.3 % | 85.7 % | 2357.4 |  |
| presidio | t1-swiss | 57.7 % | 68.1 % | 2357.4 |  |
| privacy-filter | t1-open-pii-500k | 69.8 % | 96.6 % | 2826.9 |  |
| privacy-filter | t1-openpii-1m | 78.8 % | 97.3 % | 2826.9 |  |
| privacy-filter | t1-swiss | 76.7 % | 91.1 % | 2826.9 |  |
| regex | t1-open-pii-500k | 6.3 % | 100.0 % |  |  |
| regex | t1-openpii-1m | 8.0 % | 99.4 % |  |  |
| regex | t1-swiss | 19.7 % | 99.6 % |  |  |
| regex+gliner2 | t1-open-pii-500k | 81.8 % | 96.7 % | 1244.4 |  |
| regex+gliner2 | t1-openpii-1m | 80.7 % | 98.2 % | 1244.4 |  |
| regex+gliner2 | t1-swiss | 80.3 % | 89.9 % | 1244.4 |  |
| regex+privacy-filter | t1-open-pii-500k | 70.0 % | 96.6 % | 2826.9 |  |
| regex+privacy-filter | t1-openpii-1m | 79.0 % | 97.3 % | 2826.9 |  |
| regex+privacy-filter | t1-swiss | 78.0 % | 91.3 % | 2826.9 |  |
