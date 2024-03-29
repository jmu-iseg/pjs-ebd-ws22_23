$(document).ready(sidebar_switch);

// Klappe das Menü auf und zu, wenn jemand auf den Button .sidebar-toggle klickt
function sidebar_switch() {
  $(".sidebar-toggle").on("click", function () {
    // Wenn Mobilansicht --> Aufklappen
    if ($(window).width() < 992) {
      // Wechsle Klasse, die das Menü auf- und zuklappt

      // Prüfen, ob noch von anderer Viewport-Size die Klasse zugewiesen ist
      $("body").removeClass("sidebarmin");

      $("body").toggleClass("sidebarmax");
      console.log("Wechsel Mobil"+ $(window).width());
      if (sessionStorage.getItem("key") != "min") {
        sessionStorage.setItem("sidebar", "min");
      } else {
        sessionStorage.setItem("sidebar", "max");
      };

      // Wenn Desktopansicht --> Zuklappen
    } else {
      // Wechsle Klasse, die das Menü auf- und zuklappt
      // Prüfen, ob noch von anderer Viewport-Size die Klasse zugewiesen ist
      $("body").removeClass("sidebarmax");

      $("body").toggleClass("sidebarmin");
      console.log("Wechsel Desktop" + $(window).width());
      if (sessionStorage.getItem("key") != "min") {
        sessionStorage.setItem("sidebar", "min");
      } else {
        sessionStorage.setItem("sidebar", "max");
      };

    };
  });
}