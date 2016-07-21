;(function($){

$('#add-modal').click(function(){
  $('#add-load-balance').modal('toggle');
});

$('select[name=pod]').change(function(){
  var pod = $(this).val();
  var hosts = $('select[name=host]');
  var url = '/ajax/pod/' + pod + '/hosts';
  $.get(url, {}, function(r){
    hosts.html('').append($('<option>').val('_random').text('Let Eru choose for me'));
    $.each(r, function(index, data){
      hosts.append($('<option>').val(data.name).text(data.name + ' - ' + data.ip));
    });
  });
});

$('select[name=image]').change(function(){
  var image = $(this).val();
  var ep = $('select[name=entrypoint]');
  var url = '/ajax/loadbalance/get-image-entrypoints';
  $.get(url, {image: image}, function(r){
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

  url = url.replace('{name}', $('input[name=name]').val()).replace('{sha}', $('input[name=version]').val());

  data.image = $('select[name=image]').val();
  data.podname = $('select[name=pod]').val();
  data.hostname = $('select[name=host]').val();
  data.entrypoint = $('select[name=entrypoint]').val();
  data.ncore = $('input[name=ncore]').val() || '1';
  data.comment = $('input[name=comment]').val() || '';
  data.name = $('input[name=name]').val() || '';
  data.env = $('input[name=env]').val() || '';

  console.log(data);
  $.post(url, data, function(r){
    console.log(r);
    var progressBar = $('div.progress-bar');
    var wsUrl = 'ws://' + location.host + '/websocket/check-load-balance?task=' + r.task;

    $('#add-load-balance').modal('hide');
    $('#add-loadbalance-progress').modal('show');
    progressBar.width('0').animate({width: '100%'}, 20000);
    waitForWebsocket(wsUrl, function(e){
      console.log(e.data);
      progressBar.width('100%');
      location.reload();
    });
  });
});

$('a[name=delete-balancer]').click(function(e){
  e.preventDefault();
  if (!confirm('确认删除?')) {
    return;
  }
  var self = $(this);
  var url = '/ajax/loadbalance/{id}/remove'.replace('{id}', self.data('id'));
  $.post(url, {}, function(){
    self.parent().parent().remove();
  });
});

})(jQuery);
