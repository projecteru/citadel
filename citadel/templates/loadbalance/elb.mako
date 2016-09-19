<%inherit file="/base.mako"/>
<%namespace name="utils" file="/utils.mako"/>

<%def name="title()">Balancer ${ name }</%def>

<%block name="main">
  <%call expr="utils.panel()">
    <%def name="header()">
      <h3 class="panel-title">"${ name }" Instances</h3>
    </%def>

    <table class="table">
      <thead>
        <tr>
          <th>IP</th>
          <th>ContainerID</th>
          <th>Operation</th>
        </tr>
      </thead>
      <tbody>
        % for elb in elbs:
          <tr>
            <td><a href="http://${elb.ip}/__erulb__/upstream" target="_blank">${elb.ip}</a></td>
            <td><span class="label label-${'success' if elb.is_alive() else 'danger'}">${elb.container_id}</span></td>
            <td><a class="btn btn-xs btn-warning" href="#" data-id="${elb.id}" name="delete-balancer"><span class="fui-trash"></span> Remove</a></td>
          </tr>
        % endfor
      </tbody>
    </table>
    <button class="btn btn-info btn-xs" id="refresh-btn" data-name="${name}"><span class="fui-info-circle"></span> Refresh Routes</button>
  </%call>

  <%call expr="utils.panel()">
    <%def name="header()">
      <h3 class="panel-title">"${name}" Balancing Routes</h3>
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
        % for r in routes:
          <tr>
            <td><a href="${ url_for('app.get_app', name=r.appname) }" target="_blank">${ r.appname }</a></td>
            <td>${ r.entrypoint }</td>
            <td>${ r.podname }</td>
            <td>${ r.domain }</td>
            <td><a class="btn btn-xs btn-warning" href="#" data-id="${r.id}" name="delete-route"><span class="fui-trash"></span> Remove</a></td>
          </tr>
        % endfor
      </tbody>
    </table>
  </%call>

  <div class="col-md-8 col-md-offset-2">
    <form class="form-horizontal" action="${ url_for('loadbalance.elb', name=name) }" method="POST">
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
        <div class="col-sm-10 col-sm-offset-2">
          <button class="btn btn-info" type="submit"><span class="fui-plus"></span> Add</button>
        </div>
      </div>
    </form>
  </div>

</%block>

<%def name="bottom_script()">
  <script src="/citadel/static/js/balancer.js" type="text/javascript"></script>
  <script src="/citadel/static/js/add-loadbalance.js" type="text/javascript"></script>
</%def>
