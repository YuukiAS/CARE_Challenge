To: care26challenge@163.com
Alternative recipient: care2026challenge@outlook.com
Subject: [CARE-Myocardium Test] OrganAgent – Docker Submission

Dear CARE Myocardium organizers,

Please find below our Docker submissions for the MyoPS and CineMyoPS tasks.

1. MyoPS
   Download link: https://drive.google.com/open?id=1qGb6RY5t1AkuRhpZPip2VM7Uue35roVR
   Archive: MyoPS-OrganAgent.tar.gz
   Loaded image: care-myocardium-myops:organagent
   SHA-256: 638c1d54d1c75f3514f325695025c03bd8f43625c9f2877d72841db6ee2ac73b

2. CineMyoPS
   Download link: https://drive.google.com/open?id=1JjME5rUAUvZsV1n_oH8UFNK8O7CAHJ_L
   Archive: CineMyoPS-OrganAgent.tar.gz
   Loaded image: care-myocardium-cinemyops:organagent
   SHA-256: c02db56bd52d14d3b5bbda9d204a20b7e4c061fd5e6012ffa1cebc67fb92c136

SHA-256 manifest:
https://drive.google.com/open?id=1XCHvuv5gWyVQkKblNYYyQL4bLMLeJBvq

Both images have an ENTRYPOINT and require no additional command, network access, interactive input, or other runtime instructions in our CPU-only rehearsal.

Example commands:

```bash
docker load --input MyoPS-OrganAgent.tar.gz
docker load --input CineMyoPS-OrganAgent.tar.gz

docker run --rm --network none \
  -v "$(pwd)/input:/input:ro" \
  -v "$(pwd)/output:/output" \
  care-myocardium-myops:organagent

docker run --rm --network none \
  -v "$(pwd)/input:/input:ro" \
  -v "$(pwd)/output:/output" \
  care-myocardium-cinemyops:organagent
```

The MyoPS predictions are written to /output/myops and the CineMyoPS predictions are written to /output/cinemyops. In our public validation rehearsal, the final archives produced exactly 15 MyoPS outputs and exactly 15 CineMyoPS outputs using the official /input root structure.

Please let us know if any additional information is needed.

Best regards,
OrganAgent
