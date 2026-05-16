(function () {
  function syncRowIndexes(list) {
    Array.from(list.querySelectorAll("[data-sort-row]")).forEach((row) => {
      const checkbox = row.querySelector("[data-row-check]");
      const orderInput = row.querySelector('input[name="order"]');
      if (checkbox && orderInput) {
        checkbox.value = orderInput.value;
      }
    });
  }

  function bindBulkForms() {
    document.querySelectorAll("[data-bulk-form]").forEach((form) => {
      const selectAll = form.querySelector("[data-select-all]");
      const rowChecks = Array.from(form.querySelectorAll("[data-row-check]"));
      const selectedCount = form.querySelector("[data-selected-count]");

      function updateSelectedState() {
        const checkedCount = rowChecks.filter((checkbox) => checkbox.checked).length;

        if (selectedCount) {
          selectedCount.textContent = `已选择 ${checkedCount} 项`;
        }

        if (selectAll) {
          selectAll.checked = checkedCount > 0 && checkedCount === rowChecks.length;
          selectAll.indeterminate = checkedCount > 0 && checkedCount < rowChecks.length;
        }
      }

      selectAll?.addEventListener("change", () => {
        rowChecks.forEach((checkbox) => {
          checkbox.checked = selectAll.checked;
        });
        updateSelectedState();
      });

      rowChecks.forEach((checkbox) => {
        checkbox.addEventListener("change", updateSelectedState);
      });

      form.addEventListener("click", (event) => {
        const button = event.target.closest("[data-confirm]");
        const message = button?.getAttribute("data-confirm");
        if (message && !window.confirm(message)) {
          event.preventDefault();
        }
      });

      form.addEventListener("submit", (event) => {
        if (!event.submitter?.matches("[data-save-order]")) {
          return;
        }

        const list = form.querySelector("[data-sortable-list]");
        if (list) {
          syncRowIndexes(list);
        }
      });

      updateSelectedState();
    });
  }

  function bindExportForm() {
    const form = document.querySelector("[data-export-form]");
    if (!form) {
      return;
    }

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const target = form.elements.target?.value;
      if (target) {
        window.location.href = target;
      }
    });
  }

  function bindSortableLists() {
    document.querySelectorAll("[data-sortable-list]").forEach((list) => {
      let draggedRow = null;

      list.addEventListener("click", (event) => {
        const categoryRow = event.target.closest(".category-row");
        if (
          !categoryRow ||
          event.target.closest("a, button, input, label, select, textarea")
        ) {
          return;
        }

        const panel = categoryRow.querySelector(".category-sites");
        if (panel) {
          panel.hidden = !panel.hidden;
        }
      });

      list.addEventListener("dragstart", (event) => {
        const row = event.target.closest("[data-sort-row]");
        if (!row) {
          return;
        }

        draggedRow = row;
        row.classList.add("is-dragging");
        event.dataTransfer.effectAllowed = "move";
      });

      list.addEventListener("dragover", (event) => {
        if (!draggedRow) {
          return;
        }

        event.preventDefault();
        const row = event.target.closest("[data-sort-row]");
        if (!row || row === draggedRow) {
          return;
        }

        const box = row.getBoundingClientRect();
        const before = event.clientY < box.top + box.height / 2;
        list.insertBefore(draggedRow, before ? row : row.nextElementSibling);
      });

      list.addEventListener("dragend", () => {
        draggedRow?.classList.remove("is-dragging");
        draggedRow = null;
        syncRowIndexes(list);
      });
    });
  }

  async function refreshAdminStats() {
    const categoryNodes = document.querySelectorAll("[data-category-count]");
    if (!categoryNodes.length) {
      return;
    }

    try {
      const response = await fetch("/api/stats", {
        headers: { Accept: "application/json" },
      });
      if (!response.ok) {
        return;
      }

      const stats = await response.json();
      const categories = new Map(
        stats.categories.map((category) => [category.slug, category])
      );

      categoryNodes.forEach((node) => {
        const category = categories.get(node.dataset.categoryCount);
        if (category) {
          node.textContent = `${category.count} 款`;
        }
      });
    } catch (error) {
      // Stats are nice to have; admin actions should keep working if refresh fails.
    }
  }

  function bindHeroForm() {
    const heroForm = document.querySelector("[data-hero-form]");
    if (!heroForm) {
      return;
    }

    const checks = Array.from(heroForm.querySelectorAll("[data-hero-check]"));
    const counter = heroForm.querySelector("[data-hero-count]");
    const clearButton = heroForm.querySelector("[data-clear-hero]");

    function updateHeroState(changedCheckbox) {
      let checked = checks.filter((checkbox) => checkbox.checked);

      if (checked.length > 4 && changedCheckbox) {
        changedCheckbox.checked = false;
        checked = checks.filter((checkbox) => checkbox.checked);
        window.alert("首页最多选择 4 个软件。");
      }

      if (counter) {
        counter.textContent = `已选择 ${checked.length} / 4`;
      }
    }

    checks.forEach((checkbox) => {
      checkbox.addEventListener("change", () => updateHeroState(checkbox));
    });

    clearButton?.addEventListener("click", () => {
      checks.forEach((checkbox) => {
        checkbox.checked = false;
      });
      updateHeroState();
    });

    updateHeroState();
  }

  bindBulkForms();
  bindExportForm();
  bindSortableLists();
  bindHeroForm();
  refreshAdminStats();
  window.addEventListener("focus", refreshAdminStats);
  setInterval(refreshAdminStats, 30000);
})();
