;(function($){

$(document).ready(function(){
  var anchor = window.location.hash;
  if (anchor === '#add') {
    $('#add-container-modal').modal('show');
  }
});

  update_pod_info = function($) {
    var pod = $('#add-container-form select[name=pod]').val();
    var node_selection = $('select[name=node]');
    var get_nodes_url = '/ajax/pod/' + pod + '/nodes';
    $.get(get_nodes_url, {}, function(r){
      node_selection.html('').append($('<option>').val('').text('随便'));
      for (var i=0; i<r.length; i++) {
        node_selection.append($('<option>').val(r[i].name).text(r[i].name + ' - ' + r[i].ip));
      }
    });
    var network_checkboxes = $('#network-checkbox');
    var get_networks_url = '/api/v1/pod/' + pod + '/networks';
    $.get(get_networks_url, {}, function(r){
      network_checkboxes.html("")
      for (var i=0; i<r.length; i++) {
        network_checkboxes.append('<label class="checkbox"><input type="checkbox" name="network" value="' + r[i].name + '" checked>' + r[i].name + ' - ' + r[i].subnets + '</label>');
      }
    });
  }

update_pod_info($);

$('#add-container-form select[name=pod]').change(function(){
  update_pod_info($);
});

$('#add-container-button').click(function(e){
  e.preventDefault();
  var releaseId = $('#add-container-form input[name=release]').data('id');
  var url = '/ajax/release/' + releaseId + '/deploy';
  var data = {};
  var networks = [];

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
  data.memory = form.find('select[name=memory]').val() || '512MiB';
  data.extra_env = form.find('input[name=extra_env]').val();
  var ns = form.find('input[name=network]:checked');
  for (var i=0; i<ns.length; i++) {
    networks.push($(ns[i]).val());
  }
  data.networks = networks;
  data.debug = form.find('input[name=debug]').prop('checked');
  data.count = form.find('input[name=count]').val() || '1';
  console.log('Deploy arguments:', data);

  $('#add-container-modal').modal('hide');
  $('#container-progress').modal('show');

  var logDisplay = $('#add-container-pre');
  var success = true;
  logDisplay.val('');
  oboe({url: url, method: 'POST', body: data})
    .done(function(r) {
      console.log(r);
      if (r.error) {
        console.log('Got error', r);
        success = false;
        $('#container-progress').find('.modal-header').html('<img src="http://a4.att.hudong.com/34/07/01300542856671141943075015944.png">');
        logDisplay.append(r.error + '\n');
      } else if (r.type == 'sentence') {
        logDisplay.append(r.message + '\n');
      } else {
        logDisplay.append(JSON.stringify(r) + '\n');
      }
      $(window).scrollTop($(document).height() - $(window).height());
    }).fail(function(r) {
      logDisplay.append(JSON.stringify(r) + '\n');
      $('#container-progress').find('.modal-header').html('<img src="http://a4.att.hudong.com/34/07/01300542856671141943075015944.png">');
      console.log(r);
    })
    .on('end', function() {
      console.log('Got end signal, success:', success);
      if (success == true) {
        window.location.href = window.location.href.replace(/#\w+/g, '');
      } else {
        $('#container-progress').find('.modal-header').html('<img src="http://a4.att.hudong.com/34/07/01300542856671141943075015944.png">');
      }
    })

});

})(jQuery);
