% include('header.tpl', title='TabCluster')

<form method="post" action="/tabcluster/process/">
  <fieldset>
    <legend>1. Query the endpoint</legend>
    <label class="text">Endpoint URI</label>
      <input type="text" name="endpoint" id="endpoint" placeholder="Type an endpoint URI">
    <label>SPARQL query (be sure to retrieve one single variable with literals only)</label>
    <textarea rows="6" cols="280" name="query" id="query">SELECT ?label WHERE { ?s skos:prefLabel ?label .}</textarea>
    <button type="submit" class="btn">Submit</button>
  </fieldset>
</form>


    
% include('footer.tpl')
