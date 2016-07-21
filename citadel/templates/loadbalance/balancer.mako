<%inherit file="/base.mako"/>
<%namespace name="utils" file="/utils.mako"/>

<%def name="title()">Balancer ${ balancer.name }</%def>

<%block name="main">
  <%call expr="utils.panel()">
    <%def name="header()">
      <h3 class="panel-title">${ balancer.name }</h3>
    </%def>
    IP: ${ balancer.addr }
    <button class="btn btn-info btn-xs pull-right" id="refresh-btn" data-id="${ balancer.id }"><span class="fui-info-circle"></span> Refresh</button>
  </%call>

  <%call expr="utils.panel()">
    <%def name="header()">
      <h3 class="panel-title">Balancing Records</h3>
    </%def>
    <table class="table">
      <thead>
        <tr>
          <th>App</th>
          <th>Entrypoint</th>
          <th>Pod</th>
          <th>Domain</th>
          <th>Operation</th>
        </tr>
      </thead>
      <tbody>
        % for r in records:
          <tr>
            <td>${ r.appname }</td>
            <td>${ r.entrypoint }</td>
            <td>${ r.podname }</td>
            <td>${ r.domain }</td>
            <td>
              % if analysis_dict.get(r.domain, 0):
                <a name="swither" class="btn btn-xs btn-warning" href="#" data-record-id="${ r.id }">
                  <span class="fui-pause"></span> Disable Analysis
                </a>
              % else:
                <a name="swither" class="btn btn-xs btn-warning" href="#" data-record-id="${ r.id }">
                  <span class="fui-play"></span> Enable Analysis
                </a>
              % endif
              <a class="btn btn-xs btn-warning" href="#" data-record-id="${ r.id }" name="delete-record">
                <span class="fui-trash"></span> Remove
              </a>
            </td>
          </tr>
        % endfor
      </tbody>
    </table>
  </%call>
<!--
    加一个表,显示特定的record.
-->
  <%call expr="utils.panel()">
    <%def name="header()">
      <h3 class="panel-title">Special Balancing Records</h3>
    </%def>
    <table class="table">
      <thead>
        <tr>
          <th>Domain</th>
          <th>IP</th>
          <th>Operation</th>
        </tr>
      </thead>
      <tbody>
        % for r in srecords:
          <tr>
            <td>${ r.domain }</td>
            <td>${ r.ip }</td>
            <td>
              % if analysis_dict.get(r.domain, 0):
                <a name="swither" class="btn btn-xs btn-warning" href="#" data-record-id="${ r.id }">
                  <span class="fui-pause"></span> Disable Analysis
                </a>
              % else:
                <a name="swither" class="btn btn-xs btn-warning" href="#" data-record-id="${ r.id }">
                  <span class="fui-play"></span> Enable Analysis
                </a>
              % endif
              <a class="btn btn-xs btn-warning" href="#" data-record-id="${ r.id }" name="delete-special-record">
                <span class="fui-trash"></span> Remove
              </a>
            </td>
          </tr>
        % endfor
      </tbody>
    </table>
  </%call>

<!--end-->

  <div class="col-md-8 col-md-offset-2">
    <form class="form-horizontal" action="${ url_for('loadbalance.get_balancer', id=balancer.id) }" method="POST">
      <div class="form-group">
        <label class="col-sm-2 control-label" for="">App Name</label>
        <div class="col-sm-10">
          <select id="" class="form-control" name="appname">
            % for app in all_apps:
              <option value="${ app.name }">${ app.name }</option>
            % endfor
          </select>
        </div>
      </div>
      <div class="form-group">
        <label class="col-sm-2 control-label" for="">Entrypoint</label>
        <div class="col-sm-10">
          <% entrypoints = all_apps[0].get_online_entrypoints() %>
          <select id="" class="form-control" name="entrypoint">
            % for e in entrypoints:
              <option value="${ e }">${ e }</option>
            % endfor
            <option value="_all">_all</option>
          </select>
        </div>
      </div>
      <div class="form-group">
        <label class="col-sm-2 control-label" for="">Podname</label>
        <div class="col-sm-10">
          <% pods = all_apps[0].get_online_pods() %>
          <select id="" class="form-control" name="podname">
            % for p in pods:
              <option value="${ p }">${ p }</option>
            % endfor
          </select>
        </div>
      </div>
      <div class="form-group">
        <label class="col-sm-2 control-label" for="">Domain</label>
        <div class="col-sm-10">
          <input class="form-control" type="text" name="domain">
        </div>
      </div>
      <div class="form-group">
        <label class="col-sm-2 control-label" for="">IP</label>
        <div class="col-sm-10">
            <input class="form-control" type="text" name="ip">
        </div>
      </div>
      <div class="form-group">
        <div class="col-sm-10 col-sm-offset-2">
          <button class="btn btn-info" type="submit"><span class="fui-plus"></span> Add</button>
        </div>
      </div>
    </form>
  </div>
</%block>

<%def name="bottom_script()">
  <script src="/karazhan/static/js/balancer.js" type="text/javascript"></script>
</%def>
