/* gebe body eine Klasse, wenn der Menü-Button gedrückt wird */
$('[data-bs-toggle="sidebar"]').click(function() {
  $(body).toggleClass( "sidebar-min" );
});
