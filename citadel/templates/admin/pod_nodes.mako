<%inherit file="/base.mako"/>
<%namespace name="utils" file="/utils.mako"/>

<%!
from humanize import naturalsize
%>

<%def name="title()">Pod Nodes</%def>

<%block name="main">

  <ol class="breadcrumb">
    <li><a href="${ url_for('admin.pods') }">Pod List</a></li>
    <li class="active">Node list of pod <b>${ pod.name }</b></li>
  </ol>

  <%call expr="utils.panel()">
    <%def name="header()">
      <h3 class="panel-title">Nodes</h3>
    </%def>
    <table class="table">
      <thead>
        <tr>
          <th>Name</th>
          <th>OS</th>

          <th>CPU(total)</th>
          <th>CPU(used)</th>

          <th>Memory(total)</th>
          <th>Memory(used)</th>

          <th>IP</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        % for node in nodes:
          <tr>
            <td>
              <a href="${ url_for('admin.node', podname=pod.name, nodename=node.name) }">
              % if node.available:
                <span class="label label-success">
              % else:
                <span class="label label-danger">
              % endif
                ${ node.name }
              </span>
            </a>
            </td>
            <td>${ node.info.get('OperatingSystem', 'unknown') }</td>

            <td>${ node.total_cpu_count }</td>
            <td>${ node.used_cpu_count }</td>

            <td>${ naturalsize(node.memory_total, binary=True) }</td>
            <td>${ naturalsize(node.used_mem, binary=True) }</td>

            <td>${ node.ip }</td>
            <td>
              <a name="remove-node" class="btn btn-xs btn-warning" href="#" data-delete-url="${ url_for('admin.node', nodename=node.name, podname=pod.name) }" data-nodename="${ node.name }" data-podname="${ pod.name }"><span class="fui-trash"></span></a>
              % if node.available:
                <a name="disable-node" class="btn btn-xs btn-warning" href="#" data-available="${ node.available }" data-disable-url="${ url_for('admin.node', nodename=node.name, podname=pod.name) }" data-nodename="${ node.name }" data-podname="${ pod.name }">DISABLE</a>
              % else:
                <a name="disable-node" class="btn btn-xs btn-primary" href="#" data-available="${ node.available }" data-disable-url="${ url_for('admin.node', nodename=node.name, podname=pod.name) }" data-nodename="${ node.name }" data-podname="${ pod.name }">ENABLE</a>
              % endif
            </td>
          </tr>
        % endfor
      </tbody>
    </table>
  </%call>

</%block>

<%def name="bottom_script()">

  <script>
    // Switches
    $('a[name=disable-node]').click(function (){
      var self = $(this);
      $.ajax({
        url: self.data('disable-url'),
        type: 'POST',
        dataType: 'json',
        contentType: 'application/json',
        data: JSON.stringify({available: self.data('available') != 'True'}),
        success: function(data, textStatus, jQxhr) {
          console.log('Set node availability to: ', self.data('available') != 'True', ' got response:', data);
          location.reload();
        },
        error: function(jqXhr, textStatus, errorThrown) {
          console.log('Toggle node got error: ', jqXhr, textStatus, errorThrown);
          alert(jqXhr.responseText);
        }
      });
    })
    $('a[name=remove-node]').click(function (){
      var self = $(this);
      if (!confirm('确定删除' + self.data('nodename') + '?')) { return; }
      $.ajax({
        url: self.data('delete-url'),
        type: 'DELETE',
        success: function(r) {
          console.log(r);
          location.reload();
        },
        error: function(r) {
          console.log(r);
          alert(JSON.stringify(r.responseJSON));
        }
      });
    });
  </script>

</%def>
