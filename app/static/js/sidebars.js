$(document).ready(sidebar_switch);
$(window).on('resize', sidebar_switch);

// Klappe das Menü auf und zu, wenn jemand auf den Button .sidebar-toggle klickt
function sidebar_switch() {
  // Wenn Mobilansicht --> Aufklappen
  if ($(window).width() < 992) {
     // Wechsle Klasse, die das Menü auf- und zuklappt
    $(".sidebar-toggle").on("click", function () {
      // Prüfen, ob noch von anderer Viewport-Size die Klasse zugewiesen ist
      $( ".sidebar-toggle" ).removeClass( "sidebarmin" );

      $("body").toggleClass("sidebarmax");
      console.log("Wechsel");
      if (sessionStorage.getItem("key") != "min") {
        sessionStorage.setItem("sidebar", "min");
      } else {
        sessionStorage.setItem("sidebar", "max");
      };

    });

  // Wenn Mobilansicht --> Zuklappen
  } else {
    // Wechsle Klasse, die das Menü auf- und zuklappt
    $(".sidebar-toggle").on("click", function () {
      // Prüfen, ob noch von anderer Viewport-Size die Klasse zugewiesen ist
      $( ".sidebar-toggle" ).removeClass( "sidebarmax" );

      $("body").toggleClass("sidebarmin");
      console.log("Wechsel");
      if (sessionStorage.getItem("key") != "min") {
        sessionStorage.setItem("sidebar", "min");
      } else {
        sessionStorage.setItem("sidebar", "max");
      };

    });
  }
}
