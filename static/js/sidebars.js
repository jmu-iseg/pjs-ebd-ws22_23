$(document).ready(function () {
  /* gebe body eine Klasse, wenn der Menü-Button gedrückt wird */

  if ($(window).width() < 960){
    $(".sidebar-toggle").on("click", function () {
      $("body").toggleClass("sidebarmax");
      console.log("Wechsel");
      if(sessionStorage.getItem("key") != "min") {
        sessionStorage.setItem("sidebar", "min");
      } else {
        sessionStorage.setItem("sidebar", "max");
      };
  
    });
 } else {
  $(".sidebar-toggle").on("click", function () {
    $("body").toggleClass("sidebarmin");
    console.log("Wechsel");
    if(sessionStorage.getItem("key") != "min") {
      sessionStorage.setItem("sidebar", "min");
    } else {
      sessionStorage.setItem("sidebar", "max");
    };

  });
 }
});