<%inherit file="/base.mako"/>
<%namespace name="utils" file="/utils.mako"/>

<%def name="title()">Load Balance</%def>

<%def name="more_css()">
  .progress-bar {
  -webkit-transition: none !important;
  transition: none !important;
  }
</%def>

<%def name="more_body()">
  <%call expr="utils.modal('add-load-balance')">
    <%def name="header()">
      <h3 class="modal-title">Add Load Balance</h3>
    </%def>
    <%def name="footer()">
      <button class="btn btn-warning" data-dismiss="modal"><span class="fui-cross"></span> Close</button>
      <button class="btn btn-info" id="add-load-balance-button"><span class="fui-plus"></span> Go</button>
    </%def>

    <form class="form-horizontal" action="">
      <div class="form-group">
        <label class="col-sm-2 control-label" for="">Release</label>
        <div class="col-sm-10">
          <select id="" class="form-control" name="releaseid">
            % for r in releases:
              <option value="${ r.id }">${ r.image }</option>
            % endfor
          </select>
        </div>
      </div>
      <div class="form-group">
        <label class="col-sm-2 control-label" for="">Pod</label>
        <div class="col-sm-10">
          <select name="pod" class="form-control">
            % for p in pods:
              <option value="${ p.name }">${ p.name }</option>
            % endfor
          </select>
        </div>
      </div>
      <div class="form-group">
        <label class="col-sm-2 control-label" for="">Node</label>
        <div class="col-sm-10">
          <select class="form-control" name="node">
            <option value="_random">Let Eru choose for me</option>
            % for n in nodes:
              <option value="${ n.name }">${ n.name } - ${ n.ip }</option>
            % endfor
          </select>
        </div>
      </div>
      <div class="form-group">
        <label class="col-sm-2 control-label" for="">Entrypoint</label>
        <div class="col-sm-10">
          <select class="form-control" name="entrypoint">
            % for entry in releases[0].specs.entrypoints.keys():
              <option value="${ entry }">${ entry }</option>
            % endfor
          </select>
        </div>
      </div>
      <div class="form-group">
        <label class="col-sm-2 control-label" for="">CPU</label>
        <div class="col-sm-10">
          <input class="form-control" type="number" name="cpu" value="1">
        </div>
      </div>
      <div class="form-group">
        <label class="col-sm-2 control-label" for="">Environment</label>
        <div class="col-sm-10">
          <input class="form-control" type="text" name="env" value="" placeholder="例如a=1;b=2;">
        </div>
      </div>
      <div class="form-group">
        <label class="col-sm-2 control-label" for="">Name</label>
        <div class="col-sm-10">
          <input class="form-control" type="text" name="name" value="unnamed">
        </div>
      </div>
      <div class="form-group">
        <label class="col-sm-2 control-label" for="">Comment</label>
        <div class="col-sm-10">
          <input class="form-control" type="text" name="comment" value="">
        </div>
      </div>
    </form>
  </%call>

  <%call expr="utils.modal('add-loadbalance-progress')">
    <%def name="header()">
      <h3 class="modal-title">Adding Load Balance ...</h3>
    </%def>
    <%def name="footer()">
    </%def>

    <div class="progress">
      <div class="progress-bar progress-bar-striped active" role="progressbar" aria-valuenow="100" aria-valuemin="0" aira-valuemax="100">
        <span class="sr-only">Waiting ...</span>
      </div>
    </div>
  </%call>
</%def>

<%block name="main">
  <table class="table">
    <thead>
      <tr>
        <th>Name</th>
        <th>Instance Status</th>
      </tr>
    </thead>
    <tbody>
      % for name, elbs in elb_dict.iteritems():
        <tr>
          <td><a href="${ url_for('loadbalance.elb', name=name) }">${ name }</a></td>
          <td>
            % for b in elbs:
              <span class="label label-${'success' if b.is_alive() else 'danger'}">${b.container_id[:7]} @ ${b.ip}</span>
            % endfor
          </td>
        </tr>
      % endfor
    </tbody>
  </table>

  <div class="col-md-offset-8 col-md-4">
    <button class="btn btn-info" id="add-modal"><span class="fui-plus"></span> Add Load Balance</button>
  </div>
</%block>

<%def name="bottom_script()">
  <script src="/citadel/static/js/add-loadbalance.js" type="text/javascript"></script>
</%def>
