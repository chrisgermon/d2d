#!/bin/bash
################################################################################
# D2D CLI - Command Line Interface for D2D Server
#
# Simple wrapper for D2D API operations
#
# Usage:
#   ./d2d-cli.sh status
#   ./d2d-cli.sh upload /path/to/file.pdf "Doe^John" "12345"
#   ./d2d-cli.sh destinations
#   ./d2d-cli.sh archives
################################################################################

# Configuration
D2D_URL="${D2D_URL:-http://localhost:8000}"
D2D_API_KEY="${D2D_API_KEY:-}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Helper functions
error() {
    echo -e "${RED}Error: $1${NC}" >&2
}

success() {
    echo -e "${GREEN}$1${NC}"
}

info() {
    echo -e "${BLUE}$1${NC}"
}

warning() {
    echo -e "${YELLOW}$1${NC}"
}

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    warning "jq is not installed. Output will not be formatted."
    JQ_AVAILABLE=false
else
    JQ_AVAILABLE=true
fi

# Build curl headers
build_headers() {
    local headers=()
    if [ -n "$D2D_API_KEY" ]; then
        headers+=("-H" "X-API-Key: $D2D_API_KEY")
    fi
    echo "${headers[@]}"
}

# API call wrapper
api_call() {
    local method="$1"
    local endpoint="$2"
    shift 2
    local headers=$(build_headers)

    if [ "$JQ_AVAILABLE" = true ]; then
        curl -s -X "$method" $headers "$D2D_URL$endpoint" "$@" | jq .
    else
        curl -s -X "$method" $headers "$D2D_URL$endpoint" "$@"
    fi
}

# Commands
cmd_status() {
    info "Checking D2D server status..."
    api_call GET /api/health
}

cmd_upload() {
    local file="$1"
    local patient_name="$2"
    local patient_id="$3"
    local patient_dob="$4"
    local patient_sex="$5"
    local study_desc="$6"

    if [ -z "$file" ] || [ -z "$patient_name" ] || [ -z "$patient_id" ]; then
        error "Usage: $0 upload <file> <patient_name> <patient_id> [dob] [sex] [study_desc]"
        echo "Example: $0 upload document.pdf \"Doe^John\" \"12345\" \"19800101\" \"M\" \"External Document\""
        return 1
    fi

    if [ ! -f "$file" ]; then
        error "File not found: $file"
        return 1
    fi

    info "Uploading file: $file"
    info "Patient: $patient_name (ID: $patient_id)"

    local headers=$(build_headers)
    local curl_cmd="curl -s -X POST $headers"
    curl_cmd="$curl_cmd -F \"file=@$file\""
    curl_cmd="$curl_cmd -F \"patient_name=$patient_name\""
    curl_cmd="$curl_cmd -F \"patient_id=$patient_id\""

    [ -n "$patient_dob" ] && curl_cmd="$curl_cmd -F \"patient_dob=$patient_dob\""
    [ -n "$patient_sex" ] && curl_cmd="$curl_cmd -F \"patient_sex=$patient_sex\""
    [ -n "$study_desc" ] && curl_cmd="$curl_cmd -F \"study_description=$study_desc\""

    if [ "$JQ_AVAILABLE" = true ]; then
        eval "$curl_cmd \"$D2D_URL/api/upload\"" | jq .
    else
        eval "$curl_cmd \"$D2D_URL/api/upload\""
    fi
}

cmd_destinations() {
    info "Listing DICOM destinations..."
    api_call GET /api/destinations
}

cmd_add_destination() {
    local name="$1"
    local ae_title="$2"
    local host="$3"
    local port="$4"
    local calling_ae="$5"

    if [ -z "$name" ] || [ -z "$ae_title" ] || [ -z "$host" ] || [ -z "$port" ] || [ -z "$calling_ae" ]; then
        error "Usage: $0 add-destination <name> <ae_title> <host> <port> <calling_ae>"
        echo "Example: $0 add-destination \"My PACS\" \"PACSAE\" \"10.0.0.10\" \"104\" \"D2D_SCU\""
        return 1
    fi

    info "Adding destination: $name"

    api_call POST /api/destinations \
        -H "Content-Type: application/json" \
        -d "{\"name\":\"$name\",\"ae_title\":\"$ae_title\",\"host\":\"$host\",\"port\":$port,\"calling_ae_title\":\"$calling_ae\"}"
}

cmd_verify() {
    local ae_title="$1"
    local host="$2"
    local port="$3"
    local calling_ae="$4"

    if [ -z "$ae_title" ] || [ -z "$host" ] || [ -z "$port" ] || [ -z "$calling_ae" ]; then
        error "Usage: $0 verify <ae_title> <host> <port> <calling_ae>"
        echo "Example: $0 verify \"PACSAE\" \"10.0.0.10\" \"104\" \"D2D_SCU\""
        return 1
    fi

    info "Testing connection to $host:$port..."

    api_call POST /api/destinations/verify \
        -H "Content-Type: application/json" \
        -d "{\"ae_title\":\"$ae_title\",\"host\":\"$host\",\"port\":$port,\"calling_ae_title\":\"$calling_ae\"}"
}

cmd_send() {
    local filename="$1"
    local destination="$2"

    if [ -z "$filename" ] || [ -z "$destination" ]; then
        error "Usage: $0 send <filename> <destination>"
        echo "Example: $0 send \"patient_123.dcm\" \"Intelerad PACS\""
        return 1
    fi

    info "Sending $filename to $destination..."

    api_call POST /api/send \
        -H "Content-Type: application/json" \
        -d "{\"filename\":\"$filename\",\"destination\":\"$destination\"}"
}

cmd_archives() {
    info "Listing archived DICOM files..."
    api_call GET /api/archives
}

cmd_help() {
    cat << EOF
D2D CLI - Command Line Interface for D2D Server

Usage: $0 <command> [options]

Commands:
  status                                Check D2D server status
  upload <file> <name> <id> [dob] [sex] [desc]
                                        Upload and convert a file
  destinations                          List DICOM destinations
  add-destination <name> <ae> <host> <port> <calling_ae>
                                        Add a DICOM destination
  verify <ae> <host> <port> <calling_ae>
                                        Test DICOM connection (C-ECHO)
  send <filename> <destination>         Send DICOM to PACS
  archives                              List archived DICOM files
  help                                  Show this help message

Environment Variables:
  D2D_URL                              D2D server URL (default: http://localhost:8000)
  D2D_API_KEY                          API key for authentication (optional)

Examples:
  # Check status
  $0 status

  # Upload a file
  $0 upload document.pdf "Smith^John" "12345" "19850615" "M" "Referral"

  # List destinations
  $0 destinations

  # Add a destination
  $0 add-destination "My PACS" "PACSAE" "10.0.0.10" "104" "D2D_SCU"

  # Test connection
  $0 verify "PACSAE" "10.0.0.10" "104" "D2D_SCU"

  # Send to PACS
  $0 send "20240101_patient.dcm" "My PACS"

  # View archives
  $0 archives

For more information, visit: https://github.com/chrisgermon/d2d
EOF
}

# Main command dispatcher
main() {
    if [ $# -eq 0 ]; then
        cmd_help
        exit 0
    fi

    local command="$1"
    shift

    case "$command" in
        status|health)
            cmd_status "$@"
            ;;
        upload)
            cmd_upload "$@"
            ;;
        destinations|dest)
            cmd_destinations "$@"
            ;;
        add-destination|add-dest)
            cmd_add_destination "$@"
            ;;
        verify|test)
            cmd_verify "$@"
            ;;
        send)
            cmd_send "$@"
            ;;
        archives|archive)
            cmd_archives "$@"
            ;;
        help|--help|-h)
            cmd_help
            ;;
        *)
            error "Unknown command: $command"
            echo ""
            cmd_help
            exit 1
            ;;
    esac
}

main "$@"
