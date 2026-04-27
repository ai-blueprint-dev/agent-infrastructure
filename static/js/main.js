// Atrium skill cards → copy `claude -p "<prompt>"` to clipboard.
// If the skill needs input, prompt for it first and substitute {input}.
(function () {
    const toast = document.getElementById("toast");
    let toastTimer = null;

    function showToast(msg) {
        toast.textContent = msg;
        toast.classList.add("visible");
        clearTimeout(toastTimer);
        toastTimer = setTimeout(() => toast.classList.remove("visible"), 1800);
    }

    function shellEscape(s) {
        return "'" + String(s).replace(/'/g, "'\\''") + "'";
    }

    async function copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            return true;
        } catch (e) {
            const ta = document.createElement("textarea");
            ta.value = text;
            ta.style.position = "fixed";
            ta.style.opacity = "0";
            document.body.appendChild(ta);
            ta.select();
            let ok = false;
            try { ok = document.execCommand("copy"); } catch (_) {}
            document.body.removeChild(ta);
            return ok;
        }
    }

    document.querySelectorAll(".atrium-skill").forEach((card) => {
        card.addEventListener("click", async (ev) => {
            ev.preventDefault();
            const prompt = card.dataset.prompt || "";
            const needsInput = card.dataset.needsInput === "1";
            const cmd = "claude -p " + shellEscape(prompt);
            const ok = await copyToClipboard(cmd);
            if (ok) {
                card.classList.add("copied");
                showToast(needsInput
                    ? "copied · replace {input} in the command"
                    : "copied · paste into terminal");
                setTimeout(() => card.classList.remove("copied"), 2200);
            } else {
                showToast("copy failed");
            }
        });
    });

    // Theme toggle — flips data-theme on <html>, persists in localStorage.
    // The initial paint already used the saved theme (see inline script in
    // index.html <head>), so this just handles the click.
    const themeToggle = document.getElementById("theme-toggle");
    function applyThemeLabel() {
        if (!themeToggle) return;
        const isDark = document.documentElement.dataset.theme === "dark";
        themeToggle.textContent = isDark ? "☀ light" : "☾ dark";
    }
    applyThemeLabel();
    if (themeToggle) {
        themeToggle.addEventListener("click", (ev) => {
            ev.preventDefault();
            const isDark = document.documentElement.dataset.theme === "dark";
            const next = isDark ? "light" : "dark";
            document.documentElement.dataset.theme = next;
            try { localStorage.setItem("ai-theme", next); } catch (_) {}
            applyThemeLabel();
        });
    }

    // MCP refresh — POST in the background, then soft-reload the page.
    const btnRefresh = document.getElementById("btn-refresh-mcp");
    if (btnRefresh) {
        btnRefresh.addEventListener("click", async () => {
            const original = btnRefresh.textContent;
            btnRefresh.disabled = true;
            btnRefresh.textContent = "↻ refreshing…";
            try {
                const res = await fetch("/api/refresh-mcp", { method: "POST" });
                const json = await res.json();
                showToast(`refreshed · ${json.count} connections`);
                setTimeout(() => location.reload(), 600);
            } catch (e) {
                showToast("refresh failed");
                btnRefresh.disabled = false;
                btnRefresh.textContent = original;
            }
        });
    }
})();
