/**
 * FindIt — Lightweight Progressive Enhancement Script
 */
(function () {
  'use strict';

  /**
   * Highlight the active navigation link based on current URL path.
   */
  function highlightActiveNavLink() {
    var currentPath = window.location.pathname;
    var navLinks = document.querySelectorAll('.navbar-nav .nav-link');

    navLinks.forEach(function (link) {
      var href = link.getAttribute('href');
      if (!href || href === '#' || href.startsWith('http')) {
        return;
      }

      var linkPath = new URL(href, window.location.origin).pathname;
      if (linkPath === '/' && currentPath === '/') {
        link.classList.add('active');
        link.setAttribute('aria-current', 'page');
      } else if (linkPath !== '/' && (currentPath === linkPath || currentPath.startsWith(linkPath + '/'))) {
        link.classList.add('active');
        link.setAttribute('aria-current', 'page');
      }
    });
  }

  /**
   * Auto-dismiss flash alert banners after a delay while preserving manual close.
   */
  function setupFlashAutoDismiss() {
    var alerts = document.querySelectorAll('.alert.alert-dismissible, .flash-messages .alert');
    alerts.forEach(function (alertEl) {
      if (alertEl.dataset.persist === 'true') {
        return;
      }

      window.setTimeout(function () {
        if (!document.body.contains(alertEl)) {
          return;
        }
        if (window.bootstrap && window.bootstrap.Alert) {
          var bsAlert = window.bootstrap.Alert.getOrCreateInstance(alertEl);
          bsAlert.close();
        } else {
          alertEl.classList.add('fade-out');
          window.setTimeout(function () {
            if (alertEl.parentNode) {
              alertEl.parentNode.removeChild(alertEl);
            }
          }, 350);
        }
      }, 5000);
    });
  }

  /**
   * Attach confirmation dialogs to delete forms and elements with [data-confirm].
   */
  function setupDeleteConfirmations() {
    document.addEventListener('click', function (event) {
      var trigger = event.target.closest('[data-confirm]');
      if (!trigger) {
        return;
      }
      var message = trigger.getAttribute('data-confirm') || 'Are you sure you want to proceed?';
      if (!window.confirm(message)) {
        event.preventDefault();
        event.stopPropagation();
      }
    });

    var forms = document.querySelectorAll('form');
    forms.forEach(function (form) {
      var action = (form.getAttribute('action') || '').toLowerCase();
      if (action.includes('/delete') && !form.hasAttribute('onsubmit') && !form.dataset.confirmAttached) {
        form.dataset.confirmAttached = 'true';
        form.addEventListener('submit', function (event) {
          var customMsg = form.getAttribute('data-confirm') || 'Are you sure you want to delete this item? This action cannot be undone.';
          if (!window.confirm(customMsg)) {
            event.preventDefault();
          }
        });
      }
    });
  }

  /**
   * Filter subcategory <select> options by selected category when data-category-id attributes are present.
   */
  function setupDynamicSubcategories() {
    var categorySelect = document.getElementById('category_id');
    var subcategorySelect = document.getElementById('subcategory_id');
    if (!categorySelect || !subcategorySelect) {
      return;
    }

    var allOptions = Array.from(subcategorySelect.options);
    var hasCategoryMeta = allOptions.some(function (opt) {
      return opt.dataset && opt.dataset.categoryId;
    });

    if (!hasCategoryMeta) {
      return;
    }

    function filterOptions() {
      var selectedCat = categorySelect.value;
      var currentSub = subcategorySelect.value;

      allOptions.forEach(function (opt) {
        if (!opt.value || opt.value === '0') {
          opt.hidden = false;
          opt.disabled = false;
          return;
        }
        var matches = !selectedCat || selectedCat === '0' || opt.dataset.categoryId === selectedCat;
        opt.hidden = !matches;
        opt.disabled = !matches;
      });

      var activeOpt = subcategorySelect.querySelector('option[value="' + currentSub + '"]');
      if (activeOpt && activeOpt.disabled) {
        subcategorySelect.value = '0';
      }
    }

    categorySelect.addEventListener('change', filterOptions);
    filterOptions();
  }

  /**
   * Show image preview if an image file input and preview target exist.
   */
  function setupImagePreview() {
    var fileInput = document.querySelector('input[type="file"][accept*="image"], input[name="image"]');
    var previewEl = document.getElementById('image-preview');
    if (!fileInput || !previewEl) {
      return;
    }

    fileInput.addEventListener('change', function () {
      var file = fileInput.files && fileInput.files[0];
      if (!file) {
        previewEl.classList.add('d-none');
        return;
      }
      var reader = new FileReader();
      reader.onload = function (e) {
        previewEl.src = e.target.result;
        previewEl.classList.remove('d-none');
      };
      reader.readAsDataURL(file);
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    highlightActiveNavLink();
    setupFlashAutoDismiss();
    setupDeleteConfirmations();
    setupDynamicSubcategories();
    setupImagePreview();
  });

  window.FindIt = {
    highlightActiveNavLink: highlightActiveNavLink,
    setupDynamicSubcategories: setupDynamicSubcategories
  };
})();
