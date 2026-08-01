# CARE Myocardium Test Docker Email Draft - MyoPS

当前不能发送给组织方：Docker image 未构建，下载链接和 SHA256 为空。

Subject:

```text
[CARE-Myocardium Test] OrganAgent – Docker Submission
```

Body draft for later manual use after a verified Docker export exists:

```text
Dear CARE 2026 Myocardium organizers,

We submit the Docker image for task: MyoPS.

Download link: <USER_TO_FILL_AFTER_UPLOAD>
Filename: <blocked: Docker tar.gz not generated in current environment>
SHA256: <blocked>

Load command:
gzip -dc <filename>.tar.gz | docker load

Run command:
docker run --rm -v <test-root>:/input:ro -v <output-root>:/output <image-tag>

CPU/GPU requirement:
CPU-only path is intended, but it has not been verified because Docker is unavailable on the current host.

Output layout:
/output/myops/Case*_pred.nii.gz

Contact note:
Please contact us if the container run reports an error.
```
