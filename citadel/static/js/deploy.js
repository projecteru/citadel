;(function($){

$(document).ready(function(){
  var anchor = window.location.hash;
  if (anchor === '#add') {
    $('#add-container-modal').modal('show');
  }
});

$('#add-container-form select[name=pod]').change(function(){
  var pod = $(this).val();
  var node_selection = $('select[name=node]');
  var get_nodes_url = '/ajax/pod/' + pod + '/nodes';
  $.get(get_nodes_url, {}, function(r){
    node_selection.html('').append($('<option>').val('_random').text('Let Eru choose for me'));
    for (var i=0; i<r.length; i++) {
      node_selection.append($('<option>').val(r[i].name).text(r[i].name + ' - ' + r[i].ip));
    }
  });
  var network_checkboxes = $('#network-checkbox');
  var get_networks_url = '/api/v1/pod/' + pod + '/networks';
  $.get(get_networks_url, {}, function(r){
    network_checkboxes.html("")
    for (var i=0; i<r.length; i++) {
      network_checkboxes.append('<label class="checkbox"><input type="checkbox" name="network" value="' + r[i].name + '">' + r[i].name + ' - ' + r[i].subnets + '</label>');
    }
  });
});

$('#add-container-button').click(function(e){
  e.preventDefault();
  var url = '/ajax/release/{releaseId}/deploy';
  var data = {};
  var networks = [];
  var releaseId = $('#add-container-form input[name=release]').data('id');

  url = url.replace('{releaseId}', releaseId);

  if ($('div.active #add-container-form').length) {
    var form = $('div.active #add-container-form');
  } else {
    var form = $('#add-container-form');
  }
  data.podname = form.find('select[name=pod]').val();
  data.nodename = form.find('select[name=node]').val();
  data.entrypoint = form.find('select[name=entrypoint]').val();
  data.envname = form.find('select[name=envname]').val() || '';
  data.count = form.find('input[name=count]').val() || '1';
  data.cpu = form.find('select[name=cpu]').val() || '0.5';
  data.memory = form.find('select[name=memory]').val() || '512MB';
  data.envs = form.find('input[name=envs]').val();
  var ns = form.find('input[name=network]:checked');
  for (var i=0; i<ns.length; i++) {
    networks.push($(ns[i]).val());
  }
  data.networks = networks;
  data.raw = form.find('input[name=raw]:checked').length;

  console.log(data);
  var progressBar = $('div.progress-bar');

  $('#add-container-modal').modal('hide');
  $('#container-progress').modal('show');
  progressBar.width('0').animate({width: '100%'}, 10000);
  $.post(url, data, function(r){
    if (r.error !== null) {
      alert(r.error);
      $('#container-progress').modal('hide');
      return;
    }
    $('#container-progress').modal('hide');
    window.location.href = window.location.href.replace(/#\w+/g, '');
  });
});

})(jQuery);
