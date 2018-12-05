import sqlite3
import json
from cerberus import *
from flask import g, Flask, render_template, url_for
from flask import redirect, request, Response, jsonify
from flask import make_response
import os.path, time
import werkzeug.exceptions


app = Flask(__name__)


class GeneValidator(Validator):
  def _validate_greater_than(self, other, field, value):
    """ Compare a value with value of another field.
    The rule's arguments are validated against this schema:
    {'type': 'string'}
    """
    if other not in self.document:
      return False
    if value < self.document[other]:
      self._error(field, "%s must be greater than %s." % (field, other))

  def _validate_no_duplicate(self, value, field, gene_ID):
    """ Check if an Enseml_Gene_ID already exists in the database.
    The rule's arguments are validated against this schema:
    {'type': 'boolean'}
    """
    if value :
      result = query_db('select 1 from Genes where Ensembl_Gene_ID=?', [gene_ID], one=True)
      if result:
        self._error(field, "%s is already in the database."  % gene_ID)


add_gene_schema = {
    'Ensembl_Gene_ID':
    {'required': True, 'type': 'string', 'empty': False, 'no_duplicate':True},

    'Chromosome_Name':
    {'required': True, 'type': 'string', 'empty': False},

    'Band':
    {'required': True, 'type': 'string', 'empty': False},

    'Strand':
    {'required': False, 'type': 'integer', 'empty': False},

    'Gene_Start':
    {'required': True, 'type': 'integer', 'empty': False},

    'Gene_End':
    {'required': True, 'type': 'integer', 'empty': False, 'greater_than': 'Gene_Start'},

    'Associated_Gene_Name':
    {'required': False, 'type': 'string', 'empty': False}
}

update_gene_schema = add_gene_schema
update_gene_schema['Ensembl_Gene_ID']['no_duplicate'] = False

class NotModified(werkzeug.exceptions.HTTPException):
    code = 304
    def get_response(self, environment):
        return Response(status=304)


def get_db():
  db = getattr(g, '_database', None)
  if db is None:
    db = g._database = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
  return db


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def query_db(query, args=(), one=False):
  """
  Return a nametuple resulting from a SQL query
  """
  cur = get_db().execute(query, args)
  rv = cur.fetchall()
  cur.close()
  return (rv[0] if rv else None) if one else rv


def delete_gene(id):
  conn = sqlite3.connect(DATABASE)
  c = conn.cursor()
  c.execute('delete from Genes where Ensembl_Gene_ID=?', [id])
  conn.commit()


def add_gene_to_DB(form_dict):
  conn = sqlite3.connect(DATABASE)
  c = conn.cursor()
  query = "insert into Genes ("
  for key in form_dict.keys():
    query += key + ", "
  query = query[:-2] + ")" + " values(" + len(form_dict) * "?,"
  query = query[:-1] + ");"
  c.execute(query, list(form_dict.values()))
  conn.commit()


def update_gene(form_dict):
  conn = sqlite3.connect(DATABASE)
  c = conn.cursor()
  query = "update Genes set"
  for key in form_dict.keys():
    query += " " + key + " = ?,"
  query = query[:-1] + " where Ensembl_Gene_ID = ? ;" 
  values_list = list(form_dict.values())
  values_list.append(form_dict["Ensembl_Gene_ID"])
  c.execute(query,values_list)
  conn.commit()

def gene_is_in_db(gene_ID):
  return query_db("select 1 from Genes where Ensembl_Gene_ID=?", [gene_ID])

def get_gene_fields():
  query = "select * from Genes"
  cur = get_db().execute(query)
  s = cur.description
  cur.close()
  field_list = []
  for field in s:
    field_list.append(field[0])
  return field_list


def get_compact_gene_dict(id):
  gene_dict = query_db("select * from Genes where Ensembl_Gene_ID=?", [id], one=True)
  if gene_dict:
    gene_dict = dict(gene_dict)
    gene_dict["href"] = url_for('detailed_json_gene', id=id, _external=True)
  else :
    gene_dict = {}
    gene_dict["error"] = "404 : Ce gène n'existe pas."
  return gene_dict


def get_detailed_gene_dict(id):
  gene_dict = get_compact_gene_dict(id)
  if "error" in gene_dict.keys():
    return gene_dict
  del gene_dict["Transcript_count"]
  del gene_dict["href"]
  gene_dict["transcripts"] = get_transcript_dict(id)
  return gene_dict


def get_transcript_dict(id):
  conn = sqlite3.connect(DATABASE)
  conn.row_factory = dict_factory
  c = conn.cursor()
  query = ('select Ensembl_Transcript_ID, Transcript_Start, Transcript_End '
           'from Transcripts where Ensembl_Gene_ID=?')
  c.execute(query, [id])
  transcript_dict = c.fetchall()
  conn.close()
  return transcript_dict


def get_gene_json_errors(g_dict, method):
  """
  Takes a json dict and returns its list of errors, empty if there is none.
  """
  if method == 'POST':
    schema = add_gene_schema
  if method == 'PUT':
    schema = update_gene_schema
  gene_validator = GeneValidator(schema)
  if gene_validator(g_dict): #True if there is no conflict
    return []
  else:
    return gene_validator.errors

## VIEW


@app.teardown_appcontext
def close_connection(exception):
  db = getattr(g, '_database', None)
  if db is not None:
    db.close()


@app.route('/')
def root():
  return render_template("home.html")


@app.route("/Genes/")
def global_view():
  gene_list = query_db('select * from Genes limit ?', [1000])
  return render_template("global_view.html", gene_list=gene_list)


@app.route("/Genes/view/<id>")
def gene_view(id):
  gene_info = query_db(
      'select * from genes where Ensembl_Gene_ID= ?', [id], one=True)
  query = ('select Ensembl_Transcript_ID, Transcript_Start, Transcript_End '
           'from Transcripts where Ensembl_Gene_ID=?')
  transcripts = query_db(query, [id])
  return render_template("gene_view.html",
                         gene=gene_info,
                         transcripts=transcripts)


@app.route("/Genes/del/<id>", methods=['POST'])
def del_gene(id):
  delete_gene(id)
  return redirect(url_for("global_view"))


@app.route("/Genes/new", methods=['GET', 'POST'])
def add_gene():
  if request.method == 'GET':
    fields = get_gene_fields()
    return render_template("new_gene_form.html", fields=fields)
  else:
    add_gene_to_DB(request.form)
    return redirect(url_for("global_view"))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # user = User(form.username.data, form.email.data,
        #             form.password.data)
        # db_session.add(user)
        # flash('Thanks for registering')
        return redirect(url_for('login'))
    return "TODO"


@app.route('/login')
def login():
  return "TODO"

## API

@app.route('/api/Genes/<id>', methods=['GET'])
def detailed_json_gene(id):
  """
  Fournit la représentation détaillée du gène correspondant.
  Si l’identifiant fourni ne correspond à aucun gène, retourne un objet erreur
  avec le code 404.
  """
  currver = time.ctime(os.path.getmtime(DATABASE))
  if request.if_none_match and currver in request.if_none_match:
    raise NotModified

  gene_dict = get_detailed_gene_dict(id)
  json_dict =  jsonify({id: gene_dict})

  if "error" in gene_dict.keys():
    response = make_response(json_dict, 404)
  else:
    response = make_response(json_dict)
  response.set_etag(currver)
  return response



@app.route('/api/Genes/', methods=['GET'])
def compact_json_gene(nb_of_gene=100):
  """
  Fournit les 100 premièrs gènes de la base (triés selon Ensembl_Gene_ID),
  sous la forme d’une liste de représentations compactes.
  """

  currver = time.ctime(os.path.getmtime(DATABASE))
  if request.if_none_match and currver in request.if_none_match:
    raise NotModified

  if "offset" in request.args.keys():
    offset = int(request.args["offset"])
  else:
    offset = 0
  query = ' select Ensembl_Gene_ID from Genes order by Ensembl_Gene_ID limit ? offset ?'
  results = query_db(query, [nb_of_gene, offset])
  gene_list = []
  for gene in results:
    gene_list.append(get_compact_gene_dict(gene["Ensembl_Gene_ID"]))
  gprev = offset - nb_of_gene
  if gprev < 0:
    gprev = 0
  gnext = offset + nb_of_gene
  gene_dict = {}
  compact_url = url_for("compact_json_gene", _external=True)
  gene_dict["items"] = gene_list
  gene_dict["first"] = offset + 1
  gene_dict["last"] = offset + len(gene_list)
  gene_dict["prev"] = compact_url + "?offset=" + str(gprev)
  gene_dict["next"] = compact_url + "?offset=" + str(gnext)

  response = make_response(jsonify(gene_dict))
  response.set_etag(currver)
  return response
   


@app.route('/api/Genes/<id>', methods=['POST', 'PUT'])
def add_json_gene(id=None):
  """
  METHODE POST :
  accepte une représentation détaillée d’un gène à l’exception de l’attribut 
  transcripts, et l’ajoute à la base si les conditions suivantes sont remplies.
  METHODE PUT :
  accepte le même type de données que POST /api/Genes/, avec comme contrainte 
  supplémentaire que Ensemble_Gene_ID doit être égal à la valeur <id> passée 
  dans l’URL.
  Si le gène correspondant existe, il doit être modifié conformément aux données 
  passées.
  S’il n’existe pas, il doit être créé (alternative au POST sur la collection).
  """
  g_dict = request.get_json()
  if isinstance(g_dict, dict):
    errors = get_gene_json_errors(g_dict, request.method)
    response = {}
    if errors:
      response["error"] = errors
      return jsonify(response), 400
    else :
      g_dict["Transcript_Count"] = 0
      if request.method == 'PUT' and g_dict["Ensembl_Gene_ID"] == id:
        update_gene(g_dict)
        response["modified"] = [url_for("detailed_json_gene", id = id)]        
      else:
        add_gene_to_DB(g_dict)
        response["created"] = [url_for("detailed_json_gene", id = g_dict["Ensembl_Gene_ID"])]
      return jsonify(response), 201
  elif isinstance(g_dict, list) and request.method == 'POST':
    response = {}
    response["created"] = []
    for d in g_dict:
      errors = get_gene_json_errors(d, request.method)
      if errors:
        response["error"] = errors
        return jsonify(response), 400
      else :
        d["Transcript_Count"] = 0
        add_gene_to_DB(d)
        response["created"].append([url_for("detailed_json_gene", id = d["Ensembl_Gene_ID"])])
    return jsonify(response), 201
  else :
    return "Bad Request", 400



@app.route('/api/Genes/<id>', methods=['DELETE'])
def del_gene_api(id):
  """
  supprime le gène correspondant s’il existe, et retourne avec un code 200 un objet de la forme :
  { "deleted": "<id>" }
  Si le gène correspondant n’existe pas, retourne un objet erreur avec le code 404.
  """
  result = query_db('select 1 from Genes where Ensembl_Gene_ID=?', [id], one=True)
  response = {}
  if result:
    delete_gene(id)
    response["deleted"] = str(id)
    return jsonify(response), 200
  else:
    response["error"] = "This gene doesn't exist."
    return jsonify(response), 404


  


if __name__ == "__main__":
  DATABASE = './db/ensembl_hs63_simple.sqlite'
  app.run(debug=True)
else:
  DATABASE = '/home/amren/RandomGeneDB/db/ensembl_hs63_simple.sqlite'



