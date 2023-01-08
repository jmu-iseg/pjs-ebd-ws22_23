$(document).ready(sidebar_switch);
$(window).on('resize', sidebar_switch);

function sidebar_switch() {
  if ($(window).width() < 992) {
    $(".sidebar-toggle").on("click", function () {
      $("body").toggleClass("sidebarmax");
      console.log("Wechsel");
      if (sessionStorage.getItem("key") != "min") {
        sessionStorage.setItem("sidebar", "min");
      } else {
        sessionStorage.setItem("sidebar", "max");
      };

    });
  } else {
    $(".sidebar-toggle").on("click", function () {
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
