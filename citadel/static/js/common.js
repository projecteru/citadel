;(function($){

$(document).on('mouseenter', '.btn-warning', function(){
  $(this).removeClass('btn-warning').addClass('btn-danger');
}).on('mouseleave', '.btn-danger', function(){
  $(this).removeClass('btn-danger').addClass('btn-warning');
});

})(jQuery);
