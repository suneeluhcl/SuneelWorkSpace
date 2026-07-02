#!/usr/bin/env bash
# hands/scripts/dev/java_build.sh
# Token-compact Java build wrapper: auto-detects mvnw/gradlew/mvn/gradle,
# runs the build, shows only errors/test failures/summary; full log saved.
#
# Usage: java-build [build|test|deps|verify] [project_dir] [-- extra args]
set -uo pipefail

ROOT="${SUNEEL_WORKSPACE:-$HOME/SuneelWorkSpace}"
MODE="${1:-build}"
DIR="${2:-.}"
shift $(( $# > 2 ? 2 : $# )) || true
[ "${1:-}" = "--" ] && shift

cd "$DIR" || { echo "java-build: no such directory: $DIR"; exit 1; }

LOG_DIR="$ROOT/blood/logs/dev"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/java-build-$(date +%Y%m%d-%H%M%S).log"

# JDK sanity: macOS ships a stub /usr/bin/java that fails without a real JDK.
if ! /usr/libexec/java_home >/dev/null 2>&1; then
  echo "java-build: no JDK installed."
  echo "  Suggestion: brew install --cask temurin   (then re-run)"
  exit 1
fi

# Detect build tool: project wrappers first, then global installs.
if   [ -x ./mvnw ];    then TOOL="./mvnw";  KIND=maven
elif [ -f pom.xml ] && command -v mvn >/dev/null;    then TOOL="mvn";    KIND=maven
elif [ -x ./gradlew ]; then TOOL="./gradlew"; KIND=gradle
elif { [ -f build.gradle ] || [ -f build.gradle.kts ]; } && command -v gradle >/dev/null; then TOOL="gradle"; KIND=gradle
elif [ -f pom.xml ] || [ -f build.gradle ] || [ -f build.gradle.kts ]; then
  echo "java-build: project found but no build tool. Suggestion: brew install maven (or gradle)"
  exit 1
else
  echo "java-build: no pom.xml or build.gradle in $(pwd)"
  exit 1
fi

case "$KIND:$MODE" in
  maven:build)  CMD="$TOOL -B clean install $*" ;;
  maven:test)   CMD="$TOOL -B test $*" ;;
  maven:verify) CMD="$TOOL -B verify $*" ;;
  maven:deps)   CMD="$TOOL -B dependency:tree $*" ;;
  gradle:build) CMD="$TOOL build $*" ;;
  gradle:test)  CMD="$TOOL test $*" ;;
  gradle:verify) CMD="$TOOL check $*" ;;
  gradle:deps)  CMD="$TOOL dependencies --configuration runtimeClasspath $*" ;;
  *) echo "java-build: unknown mode '$MODE' (build|test|deps|verify)"; exit 2 ;;
esac

echo "java-build [$KIND] → $CMD"
echo "full log: $LOG"

$CMD >"$LOG" 2>&1
STATUS=$?

if [ "$MODE" = "deps" ]; then
  # Dependency output is the point — show it, minus download noise.
  grep -vE "Downloading|Downloaded|Progress" "$LOG"
else
  # Compact: errors, test failures, and the build summary only.
  grep -E "ERROR|FAILED|FAILURE|BUILD SUCCESS|BUILD FAILED|BUILD SUCCESSFUL|Tests run:|tests completed" "$LOG" \
    | grep -vE "^\[INFO\] BUILD" || true
  tail -3 "$LOG"
fi

if [ $STATUS -eq 0 ]; then
  echo "✅ java-build: $MODE OK"
else
  echo "❌ java-build: $MODE failed (rc=$STATUS) — inspect $LOG"
fi
exit $STATUS
