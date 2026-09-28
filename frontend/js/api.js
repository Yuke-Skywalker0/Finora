function csrfToken() {
  const match = document.cookie.match(/(?:^|; )finora_csrf=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

const API = {
  base: window.FINORA_CONFIG.API_BASE_URL.replace(/\/$/, ""),

  async request(path, options = {}) {
    const response = await fetch(`${this.base}${path}`, {
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...(csrfToken() ? {"X-CSRF-Token": csrfToken()} : {}),
        ...(options.headers || {})
      },
      ...options
    });

    if (response.status === 204) return null;

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(data.detail || "Errore di comunicazione con il server.");
    }

    return data;
  },

  me() {
    return this.request("/api/auth/me");
  },

  googleLogin(credential) {
    return this.request("/api/auth/google", {
      method: "POST",
      body: JSON.stringify({ credential })
    });
  },

  logout() {
    return this.request("/api/auth/logout", { method: "POST" });
  },

  dashboard() {
    return this.request("/api/dashboard");
  },

  analytics() {
    return this.request("/api/dashboard/analytics");
  },

  smart() {
    return this.request("/api/dashboard/smart");
  },

  transactions() {
    return this.request("/api/transactions");
  },

  createTransaction(transaction) {
    return this.request("/api/transactions", {
      method: "POST",
      body: JSON.stringify(transaction)
    });
  },

  budgets(){return this.request("/api/budgets");},
  createBudget(x){return this.request("/api/budgets",{method:"POST",body:JSON.stringify(x)});},
  deleteBudget(id){return this.request(`/api/budgets/${id}`,{method:"DELETE"});},
  goals(){return this.request("/api/goals");},
  createGoal(x){return this.request("/api/goals",{method:"POST",body:JSON.stringify(x)});},
  deleteGoal(id){return this.request(`/api/goals/${id}`,{method:"DELETE"});},
  recurring(){return this.request("/api/recurring");},
  createRecurring(x){return this.request("/api/recurring",{method:"POST",body:JSON.stringify(x)});},
  deleteRecurring(id){return this.request(`/api/recurring/${id}`,{method:"DELETE"});},

  accounts() { return this.request("/api/accounts"); },
  createAccount(account) { return this.request("/api/accounts", {method:"POST", body:JSON.stringify(account)}); },
  deleteAccount(id) { return this.request(`/api/accounts/${id}`, {method:"DELETE"}); },

  updateTransaction(id, transaction) { return this.request(`/api/transactions/${id}`, {method: "PUT", body: JSON.stringify(transaction)}); },

  deleteTransaction(id) {
    return this.request(`/api/transactions/${id}`, { method: "DELETE" });
  }
};
