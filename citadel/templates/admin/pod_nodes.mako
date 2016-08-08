<%inherit file="/base.mako"/>
<%namespace name="utils" file="/utils.mako"/>

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
          <th>CPU(remain)</th>
          <th>Memory</th>
          <th>IP</th>
        </tr>
      </thead>
      <tbody>
        % for node in nodes:
          <tr>
            <td><a href="${ url_for('admin.get_node_containers', podname=pod.name, nodename=node.name) }">${ node.name }</a></td>
            <td>${ node.info.get('OperatingSystem', 'unknown') }</td>
            <td>${ node.total_cpu_count }</td>
            <td>${ node.used_cpu_count }</td>
            <td>${ node.cpu_count }</td>
            <td>${ node.memory_total } MB</td>
            <td>${ node.ip }</td>
          </tr>
        % endfor
      </tbody>
    </table>
  </%call>

</%block>
