<%inherit file="/base.mako"/>
<%namespace name="utils" file="/utils.mako"/>

<%def name="title()">OP Log</%def>

<%block name="main">

  <ol class="breadcrumb">
    <li><a href="${url_for('admin.index')}">Admin</a></li>
    <li class="active"><b>OP Log</b></li>
  </ol>

  <%call expr="utils.panel()">
    <%def name="header()">
      <h3 class="panel-title">OP Logs</h3>
    </%def>
    <table class="table">
      <thead>
        <tr>
          <th>🕒</th>
          <th>UserID</th>
          <th>Appname</th>
          <th>Sha</th>
          <th>Action</th>
        </tr>
      </thead>
      <tbody>
        % for oplog in oplogs:
          <tr>
            <td>${oplog.created}</td>
            <td>${oplog.user_id}</td>
            <td>${oplog.appname}</td>
            <td>${oplog.sha}</td>
            <td>${oplog.action.name}</td>
          </tr>
        % endfor
      </tbody>
    </table>
  </%call>

  ${utils.paginator(g.start, g.limit)}

</%block>
