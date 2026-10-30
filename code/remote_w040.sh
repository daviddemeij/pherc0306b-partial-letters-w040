#!/usr/bin/env bash
# Box W: focused rebuild of PHerc0306B w040's letter row and its right continuation (copy of box X's remote_topright.sh;
# selection, calibration and axis from experiments/w040-scrollfiesta-right-v1/select_w040.py).
# setup (selftests incl. the 18 s/cube long binary, Reader env) -> Socratic prediction of selection-w040.json's
# y-slabs on the GPUs -> mesh the union of the two tiles' cubes (w040 calibration: bundle pitch, extended axis, umbilicus) ->
# sheet_assemble.long for TRa/TRb/TRc in parallel, 1 h repair -> export -> Reader v3 d0 per tile -> result parts to R2.
set -euo pipefail
W=/workspace/sf; cd $W
step(){ echo "== $(date -u +%FT%TZ) $*"; }
url(){ awk -F'\t' -v n="$1" '$1==n{print $2}' "$2"; }
up(){ u=$(url "$(basename "$1")" put-urls.tsv); test -n "$u"; curl -fsS --retry 8 --retry-all-errors -T "$1" "$u"; }
up_parts(){ f=$1; n=$(basename "$f" .tar); rm -f "$f".part-*; split -b 2000m -d -a 2 "$f" "$f".part-
  for p in "$f".part-*; do up "$p"; done
  { ls "$f".part-* | xargs -n1 basename; md5sum "$f" | awk -v b="$(basename "$f")" '{print $1"  "b}'; } > $n.parts; up $n.parts; rm -f "$f".part-* "$f"; }
NCPU=$(nproc); mkdir -p logs
step setup
export DEBIAN_FRONTEND=noninteractive COPYFILE_DISABLE=1
apt-get update -qq && apt-get install -y -qq build-essential cmake python3-venv libtiff-dev liblapack-dev libgomp1 curl jq time >/dev/null
while IFS=$'\t' read -r name u; do curl -fsS --retry 8 --retry-all-errors -o "$name" "$u"; done < get-urls.tsv
cat bundle.tar.part-* > bundle.tar && sha256sum -c bundle.sha256 && tar -xf bundle.tar 2>/dev/null && rm bundle.tar bundle.tar.part-*
find . -name '._*' -type f -delete
# The bundle carries w073's selection, calibration and axis; this box works on w040's (axis extended below z 8704).
cp selection-w040.json selection-full.json; cp calibration-w040.json calibration.json; cp axis-w040.csv ct-axis/axis.csv
cp render_w040.py render_full.py
sha256sum -c binaries.sha256
for b in bin/*; do if ldd "$b" | grep -q 'not found'; then echo "missing library for $b"; exit 3; fi; done
curl -fsSL --retry 8 -o checkpoint.pt "https://media.githubusercontent.com/media/Hob3rMallow/socratic_method/7f86cbf8d38155b37fdd39449c6775ec50344b6c/releases/c3-f0-200k-20260907/checkpoint_f0_00200000.pt"
echo "54db9a59cb602ff08e3dda0acc1195ad980ab05fb660332d32fb436a0d49a175  checkpoint.pt" | sha256sum -c -
python3 -m venv --system-site-packages .venv-pred
.venv-pred/bin/pip install -q --disable-pip-version-check -e './upstream/socratic[zarr,baseline]' > logs/pred-pip.log 2>&1
.venv-pred/bin/python -c "import torch;assert torch.__version__.startswith('2.11.'),torch.__version__;print(torch.__version__,torch.cuda.device_count(),torch.cuda.get_device_name(0))"
(cd upstream/socratic && PYTHONPATH=src ../../.venv-pred/bin/python -m socratic_method.engine_pins --check) > logs/engine-pins.log 2>&1
mkdir -p prsrc && tar -xzf pred-reject-src.tar.gz -C prsrc
if (cd prsrc && gcc -O2 -D_GNU_SOURCE -include stdlib.h -Isrc -Iinclude src/tools/pred_reject.c src/extract/pred_reject.c src/common/arena.c \
  src/common/tiff_io.c src/common/ves_platform.c src/common/except.c -ltiff -lm -lpthread -o ../bin/pred_reject) > logs/prbuild.log 2>&1 \
  && bin/pred_reject --selftest 2>&1 | tail -1 | grep -q 'selftest PASSED'; then PRED_REJECT=1; else PRED_REJECT=0; echo "pred_reject unavailable"; fi
OMP_NUM_THREADS=$NCPU bin/sheet_assemble.fixed --selftest > logs/selftest-fixed.log 2>&1 || true
grep -q 'sheet_assemble selftest: 0 failure' logs/selftest-fixed.log
bash long_build.sh > logs/long-build.log 2>&1 || true
OMP_NUM_THREADS=$NCPU bin/sheet_assemble.long --selftest > logs/selftest-long.log 2>&1 || true
# The long binary is the point of this run (w073's holes came from the 9 s/cube placement cut-off); the shipped
# binary is used only if the long build fails, and that is logged loudly.
if grep -q 'sheet_assemble selftest: 0 failure' logs/selftest-long.log; then BIN=bin/sheet_assemble.long; else BIN=bin/sheet_assemble.fixed; echo "LONG BINARY FAILED; using shipped binary"; tail -20 logs/long-build.log; fi
reader_setup(){ set -e
  cat reader-inputs.tar.gz.part-* > reader-inputs.tar.gz && sha256sum -c reader.sha256 && tar -xzf reader-inputs.tar.gz && rm reader-inputs.tar.gz*
  find . -name '._*' -type f -delete
  python3 -m venv --system-site-packages .venv
  .venv/bin/pip install -q --disable-pip-version-check dynamic-network-architectures==0.4.4 pynrrd==1.1.3 numcodecs==0.16.5 zarr==3.4.1 \
    tifffile==2026.10.15 imagecodecs==2026.10.10 scipy==1.18.1 numpy==2.4.3 pillow==12.1.1 matplotlib==3.11.2 requests==2.32.5 \
    aiobotocore==3.10.0 aiohappyeyeballs==2.7.1 aiohttp==3.14.5 aioitertools==0.13.0 aiosignal==1.4.0 attrs==26.1.0 botocore==1.43.117 \
    frozenlist==1.8.0 fsspec==2026.9.0 multidict==7.2.1 propcache==0.5.4 s3fs==2026.9.0 yarl==1.25.1 nest_asyncio
  (cd reader-villa/vesuvius/src && ../../../.venv/bin/python -c 'import vesuvius.ink_detection.inference.infer, torch; assert torch.cuda.is_available(); print("reader import ok", torch.cuda.get_device_name(0))')
  .venv/bin/pip freeze > environment.txt; }
if (reader_setup) > logs/reader-setup.log 2>&1; then READER=1; else READER=0; echo "reader setup FAILED"; tail -5 logs/reader-setup.log; fi
nproc; free -g; df -h $W | tail -1
tar -cf setup-logs-W.tar logs; up setup-logs-W.tar
step "setup done (assembler $BIN, reader $READER)"

step predict start
mkdir -p pred; NGPU=$(nvidia-smi -L | wc -l)
# Slabs are dealt to the GPUs largest-first (each GPU runs its slabs one after another).
jq -r '.prediction_boxes|sort_by(-.cubes)|.[].slab' selection-full.json | awk -v n=$NGPU '{print $1" "(NR-1)%n}' > slab-gpu.txt
predict_gpu(){ g=$1
  for slab in $(awk -v g=$g '$2==g{print $1}' slab-gpu.txt); do
    region=$(jq -r --arg s "$slab" '.prediction_boxes[]|select(.slab==$s)|.bbox_zyx|"\(.[0]):\(.[1]),\(.[2]):\(.[3]),\(.[4]):\(.[5])"' selection-full.json)
    (cd upstream/socratic && CUDA_VISIBLE_DEVICES=$g PYTHONPATH=src PYTHONUNBUFFERED=1 ../../.venv-pred/bin/python -m socratic_method.predict \
      --scroll PHerc0306B --region "$region" --checkpoint $W/checkpoint.pt --out $W/pred/$slab --device cuda \
      --max-cpu-threads $(( NCPU/NGPU < 16 ? NCPU/NGPU : 16 )) --run) > logs/predict-$slab.log 2>&1 && step "predicted $slab" || step "slab $slab FAILED"
  done; }
for g in $(seq 0 $((NGPU-1))); do predict_gpu $g & done; wait
for s in $(jq -r '.prediction_boxes[].slab' selection-full.json); do test -s pred/$s/predict_receipt.json || { echo "missing receipt $s"; exit 4; }; done
step predict done

mkdir -p grid/cubes_PRED
for s in pred/*/; do for f in "$s"cubes_PRED/*.tif; do ln -sf "$W/$f" grid/cubes_PRED/; done; done
jq -r '.mesh_cubes[]' selection-full.json > keep.txt
if [ "$PRED_REJECT" = 1 ]; then mkdir -p scan; while read -r c; do { test -e grid/cubes_PRED/$c.tif && ln -sf "$(readlink -f grid/cubes_PRED/$c.tif)" scan/$c.tif; } || true; done < keep.txt
  bin/pred_reject --scan scan --out garbage.txt > logs/pred-reject.log 2>&1 || : > garbage.txt; else : > garbage.txt; fi
{ ls grid/cubes_PRED | sed 's/\.tif$//' | grep -vxF -f keep.txt; cat garbage.txt; } | sort -u > reject.txt
read UY UX PITCH < <(jq -r '"\(.umbilicus_yx[0]) \(.umbilicus_yx[1]) \(.wrap_pitch_vox)"' calibration.json)
bb=$(python3 -c "import re;c=[tuple(map(int,re.findall(r'\d+',l))) for l in open('keep.txt')];print(*[f(v[i] for v in c)+(128 if f is max else 0) for i in range(3) for f in (min,max)])")
step "mesh start ($(wc -l < keep.txt) cubes, $(wc -l < garbage.txt) garbage)"
OMP_NUM_THREADS=1 bin/grid_pipeline grid mesh --exe bin/cube_mesh.fixed --halo 13 --trim-inset 0 --skip-weld \
  --max-concurrent $NCPU --threads-per-cube 1 --subgrid $bb --skip-existing --reject-list reject.txt \
  --umb-y $UY --umb-x $UX --wrap-pitch $PITCH --axis-table ct-axis/axis.csv --grow-wind-tol 0 > logs/mesh.log 2>&1 || true
# sheet_assemble reads only .vmesh; OBJ debug dumps are ~4x larger.
find mesh/dump -name '*.obj' -delete
step "mesh done ($(ls -d mesh/dump/*/ 2>/dev/null | wc -l) cube dirs)"

TILES=$(jq -r '.tiles[].tile' selection-full.json); NT=$(echo $TILES | wc -w); THREADS=$(( NCPU / 2 / NT )); test $THREADS -ge 1 || THREADS=1
assemble(){ t=$1
  mkdir -p pile-$t; jq -r --arg t $t '.tiles[]|select(.tile==$t)|.mesh_cubes[]' selection-full.json | while read -r c; do { test -d mesh/dump/$c && ln -s $W/mesh/dump/$c pile-$t/$c; } || true; done
  jq --argjson th $THREADS --argjson rb ${REPAIR_BUDGET:-3600} '.compute.threads=$th | .repair.budget_seconds=$rb' config-assemble.json > config-$t.json
  step "$t assemble start ($(ls pile-$t | wc -l) cubes, $THREADS threads)"
  set +e
  OMP_NUM_THREADS=$THREADS OPENBLAS_NUM_THREADS=1 OMP_STACKSIZE=64M /usr/bin/time -v -o logs/assemble-$t.time \
    $BIN pile-$t out-$t config-$t.json --stop-after audit > assemble-$t.log 2>&1
  code=$?
  bin/vmesh_tifxyz.fixed out-$t/stage6_repaired.vmesh out-$t/pieces --prefix $t --top 128 --min-area 3000 --max-dim 8192 --seam-fill 2 > export-$t.log 2>&1
  ecode=$?
  set -e
  echo "{\"tile\": \"$t\", \"assemble_exit\": $code, \"export_exit\": $ecode, \"binary\": \"$BIN\"}" > out-$t/exit.json
  cp assemble-$t.log export-$t.log logs/assemble-$t.time out-$t/
  step "$t assemble=$code export=$ecode"
  if [ "$ecode" = 0 ] && [ "$READER" = 1 ]; then
    step "$t reader start"
    ( flock 9; LAB_INKWINDOW_PY=$W/.venv/bin/python LAB_INKWINDOW_VILLA_SRC=$W/reader-villa/vesuvius/src OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=1 \
        .venv/bin/python render_full.py $t --max-pieces 8 > out-$t/reader.log 2>&1 ) 9>reader.lock && step "$t reader done" || step "$t reader FAILED"
  fi
  tar --exclude='*.asr' --exclude='charts' --exclude='stage5_anchors.csv' --exclude='render.zarr' -cf result-$t.tar out-$t; up_parts result-$t.tar
  step "uploaded result-$t assemble=$code export=$ecode"
}
for t in $TILES; do assemble $t & done
wait
tar -cf logs-W.tar logs selection-full.json calibration.json ct-axis/axis.csv; up logs-W.tar
step "ALL DONE"
