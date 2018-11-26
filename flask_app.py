import sqlite3
from flask import g, Flask, render_template, url_for, redirect, request


app = Flask(__name__)

def get_db():
  db = getattr(g, '_database', None)
  if db is None:
    db = g._database = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
  return db

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

def add_new_gene(form_dict):
  conn = sqlite3.connect(DATABASE)
  c = conn.cursor()
  query = "insert into Genes values(" + len(form_dict) * "?,"
  query = query[:-1] + ");"
  c.execute(query, list(form_dict.values()))
  conn.commit()
  # return str(list(form_dict.values()))
  # return query

def get_gene_fields():
  query = "select * from Genes"
  cur = get_db().execute(query)
  s =  cur.description
  cur.close()
  field_list = []
  for field in s:
    field_list.append(field[0])
  return field_list

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
    add_new_gene(request.form)
    return redirect(url_for("global_view"))    
    #return "Vous avez envoyé : {ihi}".format(ihi=request.form['Ensembl_Gene_ID'])

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

if __name__ == "__main__":
  DATABASE = '/home/eric/Documents/M2/prog_web/RandomGeneDB/db/ensembl_hs63_simple.sqlite'
  app.run(debug=True)





