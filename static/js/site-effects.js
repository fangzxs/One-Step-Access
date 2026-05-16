/*
 * 前台轻量交互
 * ------------
 * 只做两类效果：
 * 1. 模块进入视口时淡入，页面初次加载更柔和。
 * 2. 按钮按下时改变背景色，不再使用外阴影或位移，避免界面显得跳动。
 */
(function () {
  // 这些模块会在滚动进入视口时加上 is-visible 类。
  const revealItems = document.querySelectorAll(".panel, .hero, .category-card, .site-row, .page-heading, .rank-table article");

  // IntersectionObserver 可以监听元素是否进入屏幕；不支持时页面仍然可正常使用。
  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            // 只播放一次淡入，播放后就停止观察这个元素。
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12 }
    );

    revealItems.forEach((item) => {
      // 初始隐藏由 CSS 控制，进入视口后再显示。
      item.classList.add("reveal-item");
      observer.observe(item);
    });
  }

  // 点击反馈只切换类名，具体颜色变化在 CSS 中控制。
  document.querySelectorAll(".download-btn, .btn, .category-card").forEach((item) => {
    item.addEventListener("pointerdown", () => item.classList.add("is-pressing"));
    item.addEventListener("pointerup", () => item.classList.remove("is-pressing"));
    item.addEventListener("pointerleave", () => item.classList.remove("is-pressing"));
  });

  // 实时统计刷新：访问次数和分类数量由后端统计，这里定时同步到当前页面。
  async function refreshStats() {
    const siteNodes = document.querySelectorAll("[data-site-visits]");
    const categoryNodes = document.querySelectorAll("[data-category-count]");

    if (!siteNodes.length && !categoryNodes.length) {
      return;
    }

    try {
      const response = await fetch("/api/stats", { headers: { Accept: "application/json" } });
      if (!response.ok) {
        return;
      }

      const stats = await response.json();
      const sites = new Map(stats.sites.map((site) => [String(site.index), site]));
      const categories = new Map(stats.categories.map((category) => [category.slug, category]));

      siteNodes.forEach((node) => {
        const site = sites.get(node.dataset.siteVisits);
        if (site) {
          node.textContent = `${site.visits_label} 次`;
        }
      });

      categoryNodes.forEach((node) => {
        const category = categories.get(node.dataset.categoryCount);
        if (category) {
          node.textContent = node.textContent.includes("款") ? `${category.count} 款` : String(category.count);
        }
      });
    } catch (error) {
      // 统计刷新失败不影响页面主功能，静默跳过即可。
    }
  }

  refreshStats();
  window.addEventListener("focus", refreshStats);
  setInterval(refreshStats, 30000);
})();
