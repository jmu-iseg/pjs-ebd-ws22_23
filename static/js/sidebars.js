$(document).ready(function () {
  /* gebe body eine Klasse, wenn der Menü-Button gedrückt wird */
  $(".sidebar-toggle").on("click", function () {
    $("body").toggleClass("sidebarmin");
    console.log("Wechsel");
    if(sessionStorage.getItem("key") != "min") {
      sessionStorage.setItem("sidebar", "min");
    } else {
      sessionStorage.setItem("sidebar", "max");
    };

  });

  if ($(window).width() < 960 && sessionStorage.getItem("sidebar") != "min") {
    $("body").toggleClass("sidebarmin");
 }
});