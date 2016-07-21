<%inherit file="/base.mako"/>
<%namespace name="utils" file="/utils.mako"/>

<%def name="title()">Pod Hosts</%def>

<%block name="main">

  <ol class="breadcrumb">
    <li><a href="${ url_for('admin.pods') }">Pod List</a></li>
    <li class="active">Host list of pod <b>${ pod.name }</b></li>
  </ol>

  <%call expr="utils.panel()">
    <%def name="header()">
      <h3 class="panel-title">Hosts</h3>
    </%def>
    <table class="table">
      <thead>
        <tr>
          <th>Name</th>
          <th>Mem</th>
          <th>Available Core</th>
          <th>Status</th>
          <th>Description</th>
          <th>IP</th>
        </tr>
      </thead>
      <tbody>
        % for host in hosts:
          <tr>
            <td><a href="${ url_for('admin.get_host_containers', podname=pod.name, hostname=host.name) }">${ host.name }</a></td>
            <td>${ '%.2f' % (float(host.mem) / 1024 / 1024 / 1024) } GB</td>
            <td>${ host.count }</td>
            <td>
              % if host.is_alive:
                <span class="label label-success">Running</span>
              % else:
                <span class="label label-danger">Dead</span>
              % endif
            </td>
            <td>${ pod.description }</td>
            <td>${ host.ip }</td>
          </tr>
        % endfor
      </tbody>
    </table>
  </%call>

  ${ utils.paginator() }

</%block>
