/**
 * MediCore Healthcare Systems — Client-side Interactivity
 */

document.addEventListener("DOMContentLoaded", function () {
  // Mobile Sidebar Toggle
  var toggle = document.getElementById("sidebarToggle");
  var sidebar = document.getElementById("sidebar");
  var backdrop = document.getElementById("sidebarBackdrop");

  if (toggle && sidebar) {
    toggle.addEventListener("click", function () {
      sidebar.classList.toggle("open");
    });
  }

  if (backdrop && sidebar) {
    backdrop.addEventListener("click", function () {
      sidebar.classList.remove("open");
    });
  }

  // Auto-dismiss alerts after 6 seconds (excluding critical warning or lab banners)
  var alerts = document.querySelectorAll(".alert:not(.alert-permanent)");
  alerts.forEach(function (alert) {
    setTimeout(function () {
      var bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) {
        bsAlert.close();
      }
    }, 6000);
  });
});
