import sqlite3
import json
from flask import g, Flask, render_template
from flask import url_for, redirect, request, jsonify


app = Flask(__name__)

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
  query = "insert into Genes values(" + len(form_dict) * "?,"
  query = query[:-1] + ");"
  c.execute(query, list(form_dict.values()))
  conn.commit()

def get_gene_fields():
  query = "select * from Genes"
  cur = get_db().execute(query)
  s =  cur.description
  cur.close()
  field_list = []
  for field in s:
    field_list.append(field[0])
  return field_list

def get_compact_gene_dict(id):
  conn = sqlite3.connect(DATABASE)
  conn.row_factory = dict_factory
  c = conn.cursor()
  c.execute('select * from genes where Ensembl_Gene_ID= ?', [id])
  gene_dict = c.fetchone()
  conn.close()
  if gene_dict == None:
    gene_dict = {}
    gene_dict["error"] = "404 : Ce gène n'existe pas."
  return gene_dict

def get_detailed_gene_dict(id):
  gene_dict = get_compact_gene_dict(id)
  if gene_dict["error"]:
    return gene_dict
  del gene_dict["Transcript_count"]
  gene_dict["transcripts"] = get_transcript_dict(id)
  gene_dict["href"] = url_for('gene_json', id=id, _external=True)
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
  return render_template("global_view.html", gene_list = gene_list)

@app.route("/Genes/view/<id>")
def gene_view(id):
  gene_info = query_db('select * from genes where Ensembl_Gene_ID= ?', [id], one=True)
  query = ('select Ensembl_Transcript_ID, Transcript_Start, Transcript_End '
          'from Transcripts where Ensembl_Gene_ID=?')
  transcripts = query_db(query, [id])
  return render_template("gene_view.html",
                          gene = gene_info,
                          transcripts = transcripts)

@app.route("/Genes/del/<id>", methods=['POST'])
def del_gene(id):
  delete_gene(id)
  return redirect(url_for("global_view"))

@app.route("/Genes/new", methods=['GET', 'POST'])
def add_gene():
  if request.method== 'GET':
    fields = get_gene_fields()
    return render_template("new_gene_form.html", fields = fields)
  else :
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
  gene_dict = get_detailed_gene_dict(id)
  return jsonify({id:gene_dict})   

@app.route('/api/Genes/', methods=['GET'])
def compact_json_gene(nb_of_gene=100):
  """
  Fournit les 100 premièrs gènes de la base (triés selon Ensembl_Gene_ID),
  sous la forme d’une liste de représentations compactes.
  """
  if "offset" in request.args.keys():
    offset = int(request.args["offset"])
  else :
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
  compact_url = url_for("compact_json_gene", _external = True) 
  gene_dict["items"] = gene_list
  gene_dict["first"] = offset + 1
  gene_dict["last"] = offset + len(gene_list)
  gene_dict["prev"] = compact_url + "?offset=" + str(gprev)
  gene_dict["next"] = compact_url + "?offset=" + str(gnext)
  return jsonify(gene_dict)

@app.route('/api/Genes/', methods=['POST'])
def add_json_gene(nb_of_gene=100):
  gene_request = json.dumps(request.json)
  if gene_request == None:
    return render_template("error.html")
  else:
    # if valid_gene_json(gene_request):
    #   gene_request.keys()
    #   add_gene_to_DB(gene_dict)
    #return json.dumps(gene_request)
    return type(gene_request)
    # return str(gene_request.keys())

if __name__ == "__main__":
  DATABASE = './db/ensembl_hs63_simple.sqlite'
  app.run(debug=True)
else:
  DATABASE = '/home/amren/RandomGeneDB/db/ensembl_hs63_simple.sqlite'





