/* gebe body eine Klasse, wenn der Menü-Button gedrückt wird */
$( ".sidebar-toggle" ).on( "click",function() {
  $( "body" ).toggleClass( "sidebarmin" );
  console.log("Wechsel");
});
