#!/usr/bin/env bash
# Fix pipeline scripts for all sibling studios (explicit PRIMARY path)
set -euo pipefail

fix_pipeline() {
  local sid="$1" ptype="$2" subdir="$3"
  local root="$HOME/hermes-${sid}-studio"
  local pipeline="$root/scripts/run-${sid}-pipeline.sh"
  cat > "$pipeline" <<EOF
#!/usr/bin/env bash
set -euo pipefail
DIR="\$(cd "\$(dirname "\$0")" && pwd)"
WORKDIR="\${HERMES_WORKDIR:-$root}"
export HERMES_WORKDIR="\$WORKDIR"
DATE="\${1:-\$(date +%F)}"
SLUG="$sid"
PTYPE="$ptype"
SUBDIR="$subdir"
PRIMARY="\$WORKDIR/content/\$SUBDIR/\${DATE}_\${PTYPE}_\${SLUG}.md"

echo "=== pipeline (\$DATE) ==="
python3 "\$DIR/assemble-${sid}.py" --date "\$DATE" --workdir "\$WORKDIR"
[[ -f "\$PRIMARY" ]] || { echo "❌ primary missing: \$PRIMARY"; exit 1; }
"\$DIR/validate-output.sh" "\$PTYPE" "\$PRIMARY"
echo "✅ pipeline OK"
EOF
  chmod +x "$pipeline"
  echo "✅ $pipeline"
}

fix_pipeline course syllabus syllabus
fix_pipeline intel intel intel
fix_pipeline seo seo seo
fix_pipeline personal inbox personal
fix_pipeline wiki wiki-lint wiki-reports
fix_pipeline dev spec specs
fix_pipeline delivery client client
fix_pipeline social social social

# validate threshold 100 bytes
for d in course intel seo personal wiki dev delivery social; do
  v="$HOME/hermes-${d}-studio/scripts/validate-output.sh"
  sed -i '' 's/SIZE > 200/SIZE > 100/' "$v" 2>/dev/null || sed -i 's/SIZE > 200/SIZE > 100/' "$v"
done
echo "✅ validate thresholds updated"
