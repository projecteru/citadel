;(function($){

$('#add-modal').click(function(){
  $('#add-load-balance').modal('toggle');
});

$('select[name=pod]').change(function(){
  var pod = $(this).val();
  var hosts = $('select[name=host]');
  var url = '/ajax/pod/' + pod + '/nodes';
  $.get(url, {}, function(r){
    hosts.html('').append($('<option>').val('_random').text('Let Eru choose for me'));
    $.each(r, function(index, data){
      hosts.append($('<option>').val(data.name).text(data.name + ' - ' + data.ip));
    });
  });
});

$('select[name=releaseid]').change(function(){
  var releaseId = $(this).val();
  var ep = $('select[name=entrypoint]');
  var url = '/ajax/release/' + releaseId + '/entrypoints';
  $.get(url, {}, function(r){
    ep.html('');
    $.each(r, function(index, data){
      ep.append($('<option>').val(data).text(data));
    });
  });
});

$('#add-load-balance-button').click(function(e){
  e.preventDefault();
  var url = '/ajax/loadbalance';
  var data = {};

  data.releaseid = $('select[name=releaseid]').val();
  data.podname = $('select[name=pod]').val();
  data.nodename = $('select[name=node]').val();
  data.entrypoint = $('select[name=entrypoint]').val();
  data.cpu = $('input[name=cpu]').val() || '1';
  data.comment = $('input[name=comment]').val() || '';
  data.envname = $('select[name=envname]').val() || '';

  console.log(data);
  $.post(url, data, function(r){
    console.log(r);
    location.reload();
  });
});

$('a[name=delete-balancer]').click(function(e){
  e.preventDefault();
  if (!confirm('确认删除?')) {
    return;
  }
  var self = $(this);
  var url = '/ajax/loadbalance/{id}/remove'.replace('{id}', self.data('id'));
  self.html('<span class="fui-trash"></span> Removing...');
  $.post(url, {}, function(){
    self.parent().parent().remove();
  });
});

})(jQuery);
