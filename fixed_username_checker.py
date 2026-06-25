import requests
import sys
import os
from queue import Queue

API = "https://discord.com/api/v9/unique-username/username-attempt-unauthed"
WEBHOOK = "https://discord.com/api/webhooks/1519504577173651466/6yYRuvHpdlP4-MxFMxWwyNhPA1j6RgUnlYox21o5PECB-_95S4EU2_OqYHPYv_tWKXfP"

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")
GITHUB_WORKFLOW = "checker.yml"

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Content-Type": "application/json"
})

def log(msg):
    print(msg, flush=True)

def send_webhook(name):
    """Send available username to Discord webhook"""
    if not WEBHOOK:
        return

    try:
        payload = {
            "content": f"✅ **Available Username Found!**\n`{name}`\n@everyone",
            "allowed_mentions": {"parse": ["everyone"]}
        }

        response = session.post(WEBHOOK, json=payload, timeout=10)

        if response.status_code in (200, 204):
            log(f"[WEBHOOK] ✅ Sent hit: {name}")
        else:
            log(f"[WEBHOOK] Failed: {response.status_code}")

    except Exception as e:
        log(f"[WEBHOOK ERROR] {e}")

def trigger_new_workflow_run():
    if not all([GITHUB_TOKEN, GITHUB_REPOSITORY, GITHUB_WORKFLOW]):
        log("[GITHUB] Missing environment variables")
        return False

    try:
        owner, repo = GITHUB_REPOSITORY.split("/")

        url = (
            f"https://api.github.com/repos/"
            f"{owner}/{repo}/actions/workflows/"
            f"{GITHUB_WORKFLOW}/dispatches"
        )

        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }

        log(f"[GITHUB] Triggering workflow file: {GITHUB_WORKFLOW}")

        r = requests.post(
            url,
            json={"ref": "main"},
            headers=headers,
            timeout=10
        )

        if r.status_code in (200, 204):
            log("[GITHUB] ✅ Successfully triggered new workflow run!")
            return True

        log(f"[GITHUB] Failed: {r.status_code} {r.text}")
        return False

    except Exception as e:
        log(f"[GITHUB] Error: {e}")
        return False

def load_usernames():
    names_queue = Queue()

    try:
        with open("names.txt", "r", encoding="utf-8") as f:
            usernames = [
                line.strip()
                for line in f
                if line.strip()
            ]

        if not usernames:
            log("[ERROR] names.txt is empty")
            sys.exit(1)

        for username in usernames:
            names_queue.put(username)

        log(f"[LOADED] {len(usernames)} usernames from names.txt")
        return names_queue

    except FileNotFoundError:
        log("[ERROR] names.txt not found")
        sys.exit(1)

    except Exception as e:
        log(f"[ERROR] Failed to load names.txt: {e}")
        sys.exit(1)

def check(name):
    try:
        log(f"[CHECKING] {name}")

        r = session.post(
            API,
            json={"username": name},
            timeout=15
        )

        log(f"[RESPONSE] {name} -> {r.status_code}")

        if r.status_code == 200:
            data = r.json()

            if not data.get("taken", True):
                log(f"[OPEN] {name}")

                send_webhook(name)

                with open("hits.txt", "a", encoding="utf-8") as f:
                    f.write(name + "\n")

            else:
                log(f"[TAKEN] {name}")

        elif r.status_code == 429:
            log("[RATE LIMITED] Triggering new workflow run...")

            trigger_new_workflow_run()

            log("[EXIT] Exiting current run")
            sys.exit(0)

        else:
            log(f"[ERROR] HTTP {r.status_code}")
            log(r.text[:500])

    except Exception as e:
        log(f"[ERROR] {name}: {e}")

def main():
    log("[INIT] Username checker started")

    names_queue = load_usernames()

    checked = 0

    while not names_queue.empty():
        username = names_queue.get()
        check(username)
        checked += 1

        if checked % 100 == 0:
            log(f"[PROGRESS] Checked {checked} usernames")

    log(f"[DONE] Finished checking {checked} usernames")

if __name__ == "__main__":
    main()
