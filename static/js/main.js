(function () {
  const input = document.getElementById("ticket-search");
  const tbody = document.getElementById("ticket-table-body");
  if (!input || !tbody) return;

  const activeStatus = window.__ACTIVE_STATUS__ || "";
  let debounceTimer = null;

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  function statusClass(status) {
    return "status-" + status.replace(/\s+/g, "").toLowerCase();
  }

  function formatDate(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      day: "2-digit", month: "short", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  }

  function renderRows(tickets) {
    if (!tickets.length) {
      tbody.innerHTML = `
        <tr class="empty-row">
          <td colspan="5">
            <div class="empty-state">
              <p>No tickets match this view.</p>
              <a href="/tickets/new">Create the first one →</a>
            </div>
          </td>
        </tr>`;
      return;
    }

    tbody.innerHTML = tickets.map((t) => `
      <tr onclick="window.location='/tickets/${encodeURIComponent(t.ticket_id)}'">
        <td class="col-id"><span class="ticket-id">${escapeHtml(t.ticket_id)}</span></td>
        <td class="col-name"><span class="cust-name">${escapeHtml(t.customer_name)}</span></td>
        <td class="col-subject">${escapeHtml(t.subject)}</td>
        <td class="col-status"><span class="status-pill ${statusClass(t.status)}">${escapeHtml(t.status)}</span></td>
        <td class="col-date"><span class="ts">${formatDate(t.created_at)}</span></td>
      </tr>
    `).join("");
  }

  async function runSearch() {
    const params = new URLSearchParams();
    if (input.value.trim()) params.set("search", input.value.trim());
    if (activeStatus) params.set("status", activeStatus);

    try {
      const res = await fetch(`/api/tickets?${params.toString()}`);
      if (!res.ok) throw new Error("Search request failed");
      const tickets = await res.json();
      renderRows(tickets);
    } catch (err) {
      console.error(err);
    }
  }

  input.addEventListener("input", () => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(runSearch, 250);
  });
})();
