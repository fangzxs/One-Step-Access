/*
 * 顶部导航滑动线
 * ----------------
 * 这个脚本只负责顶部导航栏里的蓝色下划线，不处理左侧分类栏。
 * 之前点击侧边栏分类时，如果顶部没有匹配的 active 菜单项，指示线会退回默认位置；
 * 现在模板会给“软件”菜单补上 active，这里也只跟随当前 active 项，避免视觉上乱跳。
 */
(function () {
  // data-nav 是顶部导航容器，data-nav-indicator 是那条会移动的蓝色线。
  const nav = document.querySelector("[data-nav]");
  const indicator = document.querySelector("[data-nav-indicator]");

  // 页面没有顶部导航时直接退出，避免后台等独立页面报错。
  if (!nav || !indicator) {
    return;
  }

  // 只收集顶部导航里的链接，左侧分类、按钮、其它链接不会影响滑动线。
  const links = Array.from(nav.querySelectorAll("a"));

  // 当前页面对应的菜单项。没有 active 时用第一个链接兜底，防止指示线没有位置。
  const activeLink = nav.querySelector("a.active") || links[0];

  // 把指示线移动到指定链接下面。
  function moveIndicator(link) {
    if (!link) {
      return;
    }

    // 用真实位置计算宽度和横向偏移，兼容桌面和手机横向滚动导航。
    const navBox = nav.getBoundingClientRect();
    const linkBox = link.getBoundingClientRect();

    indicator.style.width = `${linkBox.width}px`;
    indicator.style.transform = `translateX(${linkBox.left - navBox.left + nav.scrollLeft}px)`;
    indicator.style.opacity = "1";
  }

  // 等浏览器完成第一帧布局后再定位，避免字体或响应式布局还没稳定。
  requestAnimationFrame(() => moveIndicator(activeLink));

  // 鼠标移入顶部菜单时，指示线临时跟随悬停项。
  links.forEach((link) => {
    link.addEventListener("mouseenter", () => moveIndicator(link));
  });

  // 鼠标离开顶部导航后，指示线回到当前页面对应的菜单项。
  nav.addEventListener("mouseleave", () => moveIndicator(activeLink));

  // 窗口宽度变化会改变菜单位置，需要重新计算。
  window.addEventListener("resize", () => moveIndicator(nav.querySelector("a.active") || activeLink));
})();
