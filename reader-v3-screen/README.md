# PHerc0306B Reader v3 inference screen

[Download the release](https://github.com/daviddemeij/pherc0306b-partial-letters-w040/releases/tag/reader-v3-screen-v1.0.0)

This release preserves original Reader v3 prediction TIFFs for PHerc0306B, scan
`20250521133212` at 8.64 µm. It contains **536 production sections / 1,072 TIFFs**,
both computational directions at depth 0, and **925 supplemental TIFFs**.
There are **1,997 TIFFs** in 12 ZIP assets, totalling
**11,812,543,798 bytes (11.81 GB)**. ZIP compression and packaging do not change
the TIFF bytes or orientation.

## Coverage

This is **partial coverage**, not whole-scroll inference. Height intervals below
are half-open intervals in level-0 z voxels; winding IDs are local to each band.

| Height interval | Completed production sections | TIFFs |
|---|---:|---:|
| 2304–4608 | 120 | 240 |
| 4608–6912 | 84 | 168 |
| 6912–9216 | 120 | 240 |
| 9216–11520 | 120 | 240 |
| 11520–13824 | 92 | 184 |
| Total | 536 | 1,072 |

No completed production inference was found for **z0–2304** or
**z13824–15898**. Some covered bands have missing windings. The exact included
and missing winding lists are in [coverage.json](coverage.json). Missing lists
compare each band to the campaign's w010–w129 range; they do not establish that
all those windings have valid geometry at every height. Supplemental windows
and independent reconstructions do not fill these production coverage gaps.
Earlier estimates of 240 sections and approximately 5 GB described only the
original two-band campaign.

## Model and production recipe

- Model: [`domenicor046/reader-v3`](https://huggingface.co/domenicor046/reader-v3).
- Model revision: `aee1d64bced4eb35546348f3d276b9e2a0b99c46`.
- Checkpoint SHA-256: `ea405417450abd8ace1b8ff79ebce3adb646c5e48ab95da46844d77efe984d8a`.
- Production: an 18-layer rendered slab, depth 0, batch size 8, both directions,
  no TTA; overlap 0.5 with Hann blending. The model uses the recorded 17-plane
  context within that slab; no checkpoint context override was made.
- Villa commit: `0fb38c45b488e192566ea83ae36369cb6db92652`.
- VC3D renderer commit: `41701aa0eaa1aa765523db3f9f972b5830abf549`.

The images are uint8 prediction maps (255 represents probability 1), not human
annotations or confirmed text. Production filenames call the reverse-layer
prediction `reading` and the forward-layer prediction `opposite`. These are
computational direction labels, not a biological guarantee of the ink face.
Production maps retain the raw VC3D flat frame, with no image rotation.
Supplemental sources have their own frame and orientation conventions, recorded
in their provenance. Do not impose a single display flip on every source.
Independent reconstruction pieces use their own local UV frames. They cannot be
substituted for production winding maps using the winding label alone. Their
source geometry is not included in these inference-only ZIPs.

## Files and verification

[files.csv](files.csv) enumerates every production TIFF: band, winding, depth,
direction, dimensions, original byte size and SHA-256, ZIP asset and exact member
name. [supplemental-files.json](supplemental-files.json) records supplemental
files, source groups and hash provenance. [SHA256SUMS](SHA256SUMS) covers ZIP
assets and the three metadata manifests.

All 536 production source archives were retrieved and their multipart and
combined SHA-256 values checked against pre-existing verified retrieval
acknowledgements. Every recorded production payload hash was rechecked; each
retained TIFF's size and SHA-256 match those acknowledgements. TIFF dimensions
were checked against render receipts and all production inputs identify the
pinned checkpoint. Every release ZIP passed an integrity check and an exact
TIFF membership check against the release manifests.

The original supplemental set contains 181 TIFFs from multi-depth/TTA runs and
unchanged parent-model w040/w073 runs. Fine-tuned variants are excluded.
Supplemental hash provenance differs by source: some files have pre-existing
per-file hashes, while others have hashes computed during retrieval. Do not
interpret the supplemental manifest as proof that every file had a pre-existing
independent hash. Additional source groups, where included, are described there
with their own verification limits and geometry provenance.

The public download manifest contains outputs linked to the pinned, unchanged
Reader v3 checkpoint. Auxiliary files with only producer-declared model identity
and no recovered checkpoint hash, along with derived ensembles, are excluded
from the clean public set. They remain in the private collection audit. Repeated
TIFF bytes discovered across auxiliary archives are packaged once. The manifest
describes the enumerated and verified sources, not a proof that every possible
unnamed binary in the storage bucket has been identified as Reader v3 inference.

Only prediction TIFFs, curated provenance and licensing metadata are packaged.
CT layers, masks, model checkpoints, human annotations and internal logs are
outside this release.

## Download selected predictions

The [download helper](../code/download_reader_v3.py) requires Python 3 and only
the standard library. From a checkout of this repository:

```sh
python3 code/download_reader_v3.py --band 6912-9216 --winding w040 --list
python3 code/download_reader_v3.py --band 6912-9216 --winding w040 --direction reading
python3 code/download_reader_v3.py --kind supplemental --list
python3 code/download_reader_v3.py --kind supplemental --source w073b_rv3 --depth=-2 --direction reading
```

Without filters it downloads all production predictions. Use `--kind all` to
include supplemental files. ZIPs are downloaded whole, cached, and checked
against SHA256SUMS before extraction. Only selected TIFFs are extracted, and
each is checked against its recorded byte size and SHA-256. An invalid cached
ZIP is removed and causes a failure; run again to download a fresh copy.
Incomplete downloads and failed TIFF extraction leave no completed output.
Use `--cache` and `--output` to choose directories. The helper also works as a
standalone script by fetching the release metadata.

ZIP archives can also be downloaded directly from the release. Each contains
`LICENSE-DATA.txt` and curated `provenance.json` beside the original TIFFs.

## Organization and supplemental source index

```text
production/z02304-04608/w010/reader_v3_d+0_reading.tif
production/z02304-04608/w010/reader_v3_d+0_opposite.tif
supplemental/<source-group>/<original-TIFF-name>
additional/<source-group>/<original-piece-path>/maps/<original-TIFF-name>
```

Production paths normalize the band and winding names. Supplemental paths keep
the source group and original TIFF filenames; reconstruction pieces retain
their piece paths. The manifests supply dimensions, directions, depths, exact
ZIP membership, hashes and frame provenance. Every production section has its
reading and opposite maps; supplemental availability varies by source.

| Source group (`--source`) | TIFFs | Depth offsets |
|---|---:|---|
| `original-parent-w073-depth-minus2` | 2 | -2 |
| `original-w073-crop` | 1 | -2 |
| `reader-v3-control-repair1` | 2 | +0 |
| `row_parent` | 8 | -4, -2, +0, +2 |
| `row_parent_b` | 8 | -4, -2, +0, +2 |
| `rv3_w073_w1` | 12 | -4, -3, -2, -1, +0, +1 |
| `rv3_w073_w2` | 12 | -4, -3, -2, -1, +0, +1 |
| `rv3_w073_w3` | 12 | -4, -3, -2, -1, +0, +1 |
| `scrollfiesta-depths-T1-standalone` | 30 | -6, -3, +0, +3, +6 |
| `scrollfiesta-depths-T2-standalone` | 20 | -6, -3, +0, +3, +6 |
| `scrollfiesta-depths-T3-standalone` | 20 | -6, -3, +0, +3, +6 |
| `scrollfiesta-depths-T4-standalone` | 10 | -6, -3, +0, +3, +6 |
| `scrollfiesta-depths-T5-standalone` | 10 | -6, -3, +0, +3, +6 |
| `scrollfiesta-depths-T6-standalone` | 10 | -6, -3, +0, +3, +6 |
| `scrollfiesta-extra-T3-standalone` | 40 | -6, -3, +0, +3, +6 |
| `scrollfiesta-result-FOLD` | 2 | +0 |
| `scrollfiesta-result-T1a` | 110 | -6, -3, +0, +3, +6 |
| `scrollfiesta-result-T1b` | 100 | -6, -3, +0, +3, +6 |
| `scrollfiesta-result-T1c` | 60 | -6, -3, +0, +3, +6 |
| `scrollfiesta-result-T2a` | 70 | -6, -3, +0, +3, +6 |
| `scrollfiesta-result-T2b` | 90 | -6, -3, +0, +3, +6 |
| `scrollfiesta-result-T2c` | 30 | -6, -3, +0, +3, +6 |
| `scrollfiesta-result-TRa` | 4 | +0 |
| `scrollfiesta-result-TRb` | 4 | +0 |
| `scrollfiesta-result-TRc` | 6 | +0 |
| `scrollfiesta-result-Wa` | 6 | +0 |
| `tp_w084z11520` | 26 | -6, -5, -4, -3, -2, -1, +0, +1, +2, +3, +4, +5, +6 |
| `tp_w099z11520` | 26 | -6, -5, -4, -3, -2, -1, +0, +1, +2, +3, +4, +5, +6 |
| `tp_w113z11520` | 26 | -6, -5, -4, -3, -2, -1, +0, +1, +2, +3, +4, +5, +6 |
| `tp_w114z11520` | 26 | -6, -5, -4, -3, -2, -1, +0, +1, +2, +3, +4, +5, +6 |
| `w040_villa` | 26 | -8, -7, -6, -5, -4, -3, -2, -1, +0, +1, +2, +3, +4 |
| `w040w_villa` | 26 | -8, -7, -6, -5, -4, -3, -2, -1, +0, +1, +2, +3, +4 |
| `w073b_rv3` | 90 | -8, -7, -6, -5, -4, -3, -2, -1, +0, +1, +2, +3, +4 |


## Licensing and attribution

Inference data and metadata: **CC BY-NC 4.0**, consistent with the repository's
[data licence](../DATA_LICENSE.md) and the Vesuvius Challenge source data:
https://creativecommons.org/licenses/by-nc/4.0/ . Code: **MIT**, under the
repository's [LICENSE](../LICENSE).

Please credit David de Meij and collaborators, the Vesuvius Challenge source
data, and the Reader v3 model authors. This release does not modify the
repository's existing w040 findings or its earlier inference-v1.0.0 release.
