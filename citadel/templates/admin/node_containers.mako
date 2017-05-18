<%inherit file="/base.mako"/>
<%namespace name="utils" file="/utils.mako"/>

<%def name="title()">Node Containers</%def>

<%block name="main">

  <ol class="breadcrumb">
    <li><a href="${ url_for('admin.pods') }">Pod List</a></li>
    <li><a href="${ url_for('admin.get_pod_nodes', name=pod.name) }">Node list of pod <b>${ pod.name }</b></a></li>
    <li class="active">Container list of node <b>${ node.name }</b></li>
  </ol>

  <%call expr="utils.panel()">
    <%def name="header()">
      <h3 class="panel-title">Containers</h3>
    </%def>

    <%call expr="utils.container_list(containers)">
      <button name="replace-container" class="btn btn-primary pull-left" data-toggle="modal" data-target="#replace-container-modal"><span class="fui-apple"></span>换新</button>
    </%call>
  </%call>

  <%call expr="utils.modal('replace-container-modal')">
    <%def name="header()">
      <h3 class="modal-title">Replace Container</h3>
    </%def>

    <form id="replace-container-form" class="form-horizontal" action="">
      <p>会把所有容器换新哦, 如果你想要的是迁移到其他 node 上, 需要先把这个 node 禁用</p>
    </form>

    <%def name="footer()">
      <button class="btn btn-warning" id="close-modal" data-dismiss="modal"><span class="fui-cross"></span>Close</button>
      <button class="btn btn-info" id="replace-container-button">干!</button>
    </%def>
  </%call>

  <%call expr="utils.modal('replace-container-progress', dialog_class='modal-lg')">
    <%def name="header()">
      <h3 class="modal-title">正在换新...</h3>
    </%def>
    <%def name="footer()">
    </%def>

    <pre id="replace-container-pre"></pre>

  </%call>

  <script>
    $('button[id=replace-container-button]').click(function(e){
      e.preventDefault();
      if (!$('input[name=container-id]:checked').length) {
        return;
      }

      var data = {};
      var container_ids = [];
      data.sha = $('select[name=release]').val();
      $.each($('input[name=container-id]:checked'), function(){
        container_ids.push($(this).val());
      })
      data.container_ids = container_ids;

      $('#replace-container-modal').modal('hide');
      $('#replace-container-progress').modal('show');

      var logDisplay = $('#replace-container-pre');
      var success = true;
      oboe({url: "${ url_for('ajax.replace_containers') }", method: 'POST', body: data})
        .done(function(r) {
          console.log(r);
          if (r.error) {
            console.log('replace Container got error', r);
            success = false;
            $('#replace-container-progress').find('.modal-header').html('<img src="http://a4.att.hudong.com/34/07/01300542856671141943075015944.png">');
            logDisplay.append(r.error + '\n');
          } else if (r.type == 'sentence') {
            logDisplay.append(r.message + '\n');
          } else {
            logDisplay.append(JSON.stringify(r) + '\n');
          }
          $(window).scrollTop($(document).height() - $(window).height());
        }).fail(function(r) {
          logDisplay.append(JSON.stringify(r) + '\n');
          $('#replace-container-progress').find('.modal-header').html('<img src="http://a4.att.hudong.com/34/07/01300542856671141943075015944.png">');
          console.log(r);
        })
        .on('end', function() {
          console.log('Got end signal, success:', success);
          if (success == true) {
            window.location.href = window.location.href.replace(/#\w+/g, '');
          } else {
          $('#replace-container-progress').find('.modal-header').html('<img src="http://a4.att.hudong.com/34/07/01300542856671141943075015944.png">');
          }
        })
    })
  </script>

</%block>
