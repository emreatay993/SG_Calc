import clr
clr.AddReference("System.Windows.Forms")
clr.AddReference('System.Drawing')
import System.Drawing
from System.Windows.Forms import Application, Form, ComboBox, Button, DialogResult, Label, OpenFileDialog, MessageBox, MessageBoxButtons

class MyForm(Form):
    def __init__(self, labelText, itemsList):
        self.Text = "Get Solution Environment"
        self.Width = 1200
        self.Height = 300
        self.selected_item = None  # Variable to store the selected item
        self.initUI(labelText, itemsList)

    def initUI(self, labelText, itemsList):
        self.Controls.Clear()  # Clear existing controls

        self.label = Label()
        self.label.Text = labelText
        self.label.Location = System.Drawing.Point(50, 20)
        self.label.Width = 1000
        self.label.Height = 30

        self.comboBox = ComboBox()
        self.comboBox.Location = System.Drawing.Point(50, 60)
        self.comboBox.Width = 1000
        items = System.Array[str](itemsList)
        self.comboBox.Items.AddRange(items)

        self.okButton = Button()
        self.okButton.Text = "Click OK to continue"
        self.okButton.Location = System.Drawing.Point(350, 110)
        self.okButton.Width = 500
        self.okButton.Height = 40
        self.okButton.Click += self.okButton_Click

        self.Controls.Add(self.label)
        self.Controls.Add(self.comboBox)
        self.Controls.Add(self.okButton)

    def okButton_Click(self, sender, event_args):
        self.selected_item = self.comboBox.SelectedItem
        self.DialogResult = DialogResult.OK

class InputForm(Form):
    def __init__(self, form_title="Enter Custom String", label_text="Enter custom string:"):
        self.Text = form_title
        self.Width = 400
        self.Height = 150
        self.initUI(label_text)

    def initUI(self, label_text):
        self.label = Label()
        self.label.Text = label_text
        self.label.Location = System.Drawing.Point(20, 20)

        self.textBox = System.Windows.Forms.TextBox()
        self.textBox.Location = System.Drawing.Point(20, 50)
        self.textBox.Width = 350

        self.okButton = Button()
        self.okButton.Text = "OK"
        self.okButton.Location = System.Drawing.Point(150, 90)
        self.okButton.Click += self.okButton_Click

        self.Controls.Add(self.label)
        self.Controls.Add(self.textBox)
        self.Controls.Add(self.okButton)

    def okButton_Click(self, sender, event_args):
        self.DialogResult = DialogResult.OK


# Run the forms (first one is for analysis environment)
firstForm = MyForm("Select an analysis environment (should be a unique name):",DataModel.AnalysisNames)
result1 = firstForm.ShowDialog()
if result1 == DialogResult.OK:
    print("Selected environment:", firstForm.selected_item)
    sol_selected_environment = DataModel.GetObjectsByName(firstForm.selected_item)[0].Solution

