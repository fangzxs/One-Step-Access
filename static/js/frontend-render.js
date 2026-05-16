(function () {
  const page = document.querySelector("[data-page]");

  if (!page) {
    return;
  }

  const text = (value) =>
    String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");

  const getJson = async (url) => {
    const response = await fetch(url, { headers: { Accept: "application/json" } });
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`);
    }
    return response.json();
  };

  const iconHtml = (site, className) => {
    const logo = text(site.logo_text || site.name.slice(0, 2) || "S");
    const color = text(site.logo_color || "#2563eb");
    const favicon = text(site.favicon_url || "");

    if (favicon) {
      return `
        <span class="${className} auto-logo has-favicon" style="--logo-color: ${color}">
          <img src="${favicon}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.hidden=true; this.nextElementSibling.hidden=false;">
          <span hidden>${logo}</span>
        </span>
      `;
    }

    return `
      <span class="${className} auto-logo" style="--logo-color: ${color}">
        <span>${logo}</span>
      </span>
    `;
  };

  const siteRowHtml = (site) => {
    const tags = (site.tags || [])
      .slice(0, 2)
      .map((tag) => `<a href="/?q=${encodeURIComponent(tag)}">${text(tag)}</a>`)
      .join("");

    return `
      <article class="site-row" data-row-url="${text(site.visit_url)}" role="link" tabindex="0">
        <a class="site-logo-link" href="${text(site.visit_url)}" target="_blank" rel="noopener">
          ${iconHtml(site, "site-logo")}
        </a>
        <div class="site-main">
          <div class="site-heading">
            <a href="${text(site.visit_url)}" target="_blank" rel="noopener">${text(site.name)}</a>
            <span>${text(site.version)}</span>
          </div>
          <p>${text(site.description)}</p>
        </div>
        <div class="site-tags">${tags}</div>
        <span class="muted">${text(site.updated_label)}</span>
        <span class="muted" data-site-visits="${site.index}">${text(site.visits_label)} 次</span>
        <a class="download-btn" href="${text(site.visit_url)}" target="_blank" rel="noopener">访问</a>
      </article>
    `;
  };

  const renderPopular = (sites) => {
    const target = document.querySelector("[data-home-popular]");
    if (!target) {
      return;
    }

    target.innerHTML = `
      <h2>本周热门</h2>
      <ol class="ranking-list">
        ${sites
          .map(
            (site, index) => `
              <li>
                <span class="rank-badge">${index + 1}</span>
                <a class="rank-logo-link" href="${text(site.visit_url)}" target="_blank" rel="noopener">
                  ${iconHtml(site, "rank-logo")}
                </a>
                <div class="rank-info">
                  <a href="${text(site.visit_url)}" target="_blank" rel="noopener">${text(site.name)}</a>
                  <small data-site-visits="${site.index}">${text(site.visits_label)} 次访问</small>
                </div>
              </li>
            `
          )
          .join("")}
      </ol>
      <a class="wide-link" href="/rankings">查看全部排行 →</a>
    `;
  };

  const renderRecommended = (sites) => {
    const target = document.querySelector("[data-home-recommended]");
    if (!target) {
      return;
    }

    if (!sites.length) {
      target.remove();
      return;
    }

    target.innerHTML = `
      <div class="panel-title-row">
        <h2>编辑推荐</h2>
        <a href="/">查看全部 →</a>
      </div>
      <div class="recommend-list">
        ${sites
          .map(
            (site) => `
              <a href="${text(site.visit_url)}" target="_blank" rel="noopener">
                ${iconHtml(site, "recommend-logo")}
                <span>
                  <strong>${text(site.name)}</strong>
                  <small>${text(site.description)}</small>
                </span>
              </a>
            `
          )
          .join("")}
      </div>
    `;
  };

  const compactSiteHtml = (site) => `
    <a class="compact-site" href="${text(site.visit_url)}" target="_blank" rel="noopener">
      ${iconHtml(site, "recommend-logo")}
      <span>
        <strong>${text(site.name)}</strong>
        <small>${text(site.description)}</small>
      </span>
    </a>
  `;

  const renderRecent = (sites) => {
    const target = document.querySelector("[data-home-recent]");
    if (!target) {
      return;
    }

    if (!sites.length) {
      target.remove();
      return;
    }

    target.innerHTML = `
      <div class="panel-title-row">
        <h2>最近添加</h2>
      </div>
      <div class="compact-site-list">
        ${sites.map(compactSiteHtml).join("")}
      </div>
    `;
  };

  const heroHtml = (sites) => `
    <section class="hero">
      <div class="hero-copy">
        <h1>发现优秀软件</h1>
        <p class="subtitle">高效、安全、便捷的软件导航平台</p>
        <p>收录优质软件与常用网站<br />快速找到真正需要的工具</p>
        <div class="hero-actions"></div>
      </div>
      <div class="hero-art" aria-hidden="true">
        <div class="cube box"></div>
        ${sites
          .map(
            (site, index) => `
              <div class="floating-card card-${index + 1}">
                ${iconHtml(site, "hero-logo")}
              </div>
            `
          )
          .join("")}
      </div>
    </section>
  `;

  const emptySearchHtml = `
    <div class="empty-state search-empty">
      <h2>没有找到匹配的软件</h2>
      <p>可以换个关键词，比如软件名称、公司名、分类名或官网域名。</p>
      <a class="btn primary" href="/">返回全部软件</a>
    </div>
  `;

  const renderHome = async () => {
    const query = new URLSearchParams(window.location.search).get("q")?.trim() || "";
    const data = await getJson(`/api/home${query ? `?q=${encodeURIComponent(query)}` : ""}`);

    renderPopular(data.popular_sites || []);
    renderRecommended(data.recommended_sites || []);
    renderRecent(data.recent_sites || []);

    if (data.query) {
      page.innerHTML = `
        <section class="search-summary">
          <div>
            <span>搜索结果</span>
            <h1>“${text(data.query)}”</h1>
            <p>找到 ${data.result_count} 个相关软件，结果已按匹配度和访问热度排序。</p>
          </div>
          <a class="btn ghost" href="/">清除搜索</a>
        </section>
        <section id="latest" class="section-head result-head">
          <div>
            <h2>相关软件</h2>
            <p>优先展示名称、分类、官网域名和简介匹配的软件。</p>
          </div>
        </section>
        <div class="search-result-list">
          ${(data.latest_sites || []).map(siteRowHtml).join("") || emptySearchHtml}
        </div>
      `;
      return;
    }

    page.innerHTML = `
      ${heroHtml(data.hero_sites || [])}
      <section id="latest" class="section-head result-head">
        <div>
          <h2>${text(data.default_category_name || "常用软件")}</h2>
          <p>共收录 ${text(data.default_category_count || (data.latest_sites || []).length)} 款相关软件与工具</p>
        </div>
        <a href="/category/${encodeURIComponent(data.default_category || "")}">查看全部 →</a>
      </section>
      <div class="site-list">
        ${(data.latest_sites || []).map(siteRowHtml).join("")}
      </div>
    `;
  };

  const renderCategory = async () => {
    const slug = page.dataset.categorySlug;
    const data = await getJson(`/api/category/${encodeURIComponent(slug)}`);
    const category = data.category;
    document.title = `${category.name} - SoftHub`;

    page.innerHTML = `
      <section class="page-heading">
        <span class="round-icon">${text((category.name || "").slice(0, 1))}</span>
        <div>
          <h1>${text(category.name)}</h1>
          <p>共收录 <span data-category-count="${text(category.slug)}">${category.count}</span> 款相关软件与工具</p>
        </div>
      </section>
      <div class="site-list full">
        ${(data.sites || []).map(siteRowHtml).join("") || '<div class="empty-state">这个分类下暂时没有匹配的软件。</div>'}
      </div>
    `;
  };

  const renderRankings = async () => {
    const data = await getJson("/api/rankings");
    page.innerHTML = `
      <section class="page-heading">
        <span class="round-icon">榜</span>
        <div>
          <h1>软件排行榜</h1>
          <p>按访问热度排序，快速发现大家正在使用的工具。</p>
        </div>
      </section>
      <div class="rank-table">
        ${(data.sites || [])
          .map(
            (site, index) => `
              <article data-row-url="${text(site.visit_url)}" role="link" tabindex="0">
                <span class="rank-number">${index + 1}</span>
                ${iconHtml(site, "recommend-logo")}
                <div>
                  <a href="${text(site.visit_url)}" target="_blank" rel="noopener">${text(site.name)}</a>
                  <p>${text(site.description)}</p>
                </div>
                <strong data-site-visits="${site.index}">${text(site.visits_label)} 次</strong>
                <a class="download-btn" href="${text(site.visit_url)}" target="_blank" rel="noopener">访问</a>
              </article>
            `
          )
          .join("")}
      </div>
    `;
  };

  const bindPressStates = () => {
    document.querySelectorAll(".download-btn, .btn, .category-card").forEach((item) => {
      item.addEventListener("pointerdown", () => item.classList.add("is-pressing"));
      item.addEventListener("pointerup", () => item.classList.remove("is-pressing"));
      item.addEventListener("pointerleave", () => item.classList.remove("is-pressing"));
    });
  };

  const bindRowLinks = () => {
    document.querySelectorAll("[data-row-url]").forEach((row) => {
      row.addEventListener("click", (event) => {
        if (event.target.closest("a, button, input, select, textarea")) {
          return;
        }
        window.open(row.dataset.rowUrl, "_blank", "noopener");
      });

      row.addEventListener("keydown", (event) => {
        if (event.key !== "Enter" && event.key !== " ") {
          return;
        }
        if (event.target.closest("a, button, input, select, textarea")) {
          return;
        }
        event.preventDefault();
        window.open(row.dataset.rowUrl, "_blank", "noopener");
      });
    });
  };

  const renderers = {
    home: renderHome,
    category: renderCategory,
    rankings: renderRankings,
  };

  (async () => {
    try {
      await renderers[page.dataset.page]();
      bindPressStates();
      bindRowLinks();
    } catch (error) {
      page.innerHTML = '<section class="empty-state">页面数据加载失败，请稍后再试。</section>';
    }
  })();
})();
