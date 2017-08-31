# -*- coding: utf-8 -*-
r"""
Sequence Models and Long-Short Term Memory Networks
===================================================

A recurrent neural network is a network that maintains some kind of
state. For example, its output could be used as part of the next input,
so that information can propogate along as the network passes over the
sequence. In the case of an LSTM, for each element in the sequence,
there is a corresponding *hidden state* `h_t`, which in principle
can contain information from arbitrary points earlier in the sequence.
We can use the hidden state to predict words in a language model,
part-of-speech tags, and a myriad of other things.


In Pytorch's LSTM:
all of its inputs are 3D tensors. The first axis is the sequence itself, the second
indexes instances in the mini-batch, and the third indexes elements of
the input.
"""

# Inspired by PyTorch Tutorial
# Author: Reza Zangeneh

import torch
import torch.autograd as autograd
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim

torch.manual_seed(1)

######################################################################

lstm = nn.LSTM(3, 3)  # Input dim is 3, output dim is 3
inputs = [autograd.Variable(torch.randn((1, 3)))
          for _ in range(5)]  # make a sequence of length 5

# initialize the hidden state.
hidden = (autograd.Variable(torch.randn(1, 1, 3)),
          autograd.Variable(torch.randn((1, 1, 3))))
for i in inputs:
    # Step through the sequence one element at a time.
    # after each step, hidden contains the hidden state.
    out, hidden = lstm(i.view(1, 1, -1), hidden)

# alternatively, we can do the entire sequence all at once.
# the first value returned by LSTM is all of the hidden states throughout
# the sequence. the second is just the most recent hidden state
# (compare the last slice of "out" with "hidden" below, they are the same)
# The reason for this is that:
# "out" will give you access to all hidden states in the sequence
# "hidden" will allow you to continue the sequence and backpropogate,
# by passing it as an argument  to the lstm at a later time
# Add the extra 2nd dimension
inputs = torch.cat(inputs).view(len(inputs), 1, -1)
hidden = (autograd.Variable(torch.randn(1, 1, 3)), autograd.Variable(
    torch.randn((1, 1, 3))))  # clean out hidden state
out, hidden = lstm(inputs, hidden)
print(out)
print(hidden)


######################################################################
# Prepare data:

def prepare_sequence(seq, to_ix):
    idxs = [to_ix[w] for w in seq]
    tensor = torch.LongTensor(idxs)
    return autograd.Variable(tensor)


training_data = [
    ("The dog ate the apple".split(), ["DET", "NN", "V", "DET", "NN"]),
    ("Everybody read that book".split(), ["NN", "V", "DET", "NN"])
]
word_to_ix = {}
for sent, tags in training_data:
    for word in sent:
        if word not in word_to_ix:
            word_to_ix[word] = len(word_to_ix)
print(word_to_ix)
tag_to_ix = {"DET": 0, "NN": 1, "V": 2}

# These will usually be more like 32 or 64 dimensional.
# We will keep them small, so we can see how the weights change as we train.
EMBEDDING_DIM = 6
HIDDEN_DIM = 6

######################################################################
# Create the model:


class LSTMTagger(nn.Module):

    def __init__(self, embedding_dim, hidden_dim, vocab_size, tagset_size):
        super(LSTMTagger, self).__init__()
        self.hidden_dim = hidden_dim

        self.word_embeddings = nn.Embedding(vocab_size, embedding_dim)

        # The LSTM takes word embeddings as inputs, and outputs hidden states
        # with dimensionality hidden_dim.
        self.lstm = nn.LSTM(embedding_dim, hidden_dim)

        # The linear layer that maps from hidden state space to tag space
        self.hidden2tag = nn.Linear(hidden_dim, tagset_size)
        self.hidden = self.init_hidden()

    def init_hidden(self):
        # Before we've done anything, we dont have any hidden state.
        # The axes semantics are (num_layers, minibatch_size, hidden_dim)
        return (autograd.Variable(torch.zeros(1, 1, self.hidden_dim)),
                autograd.Variable(torch.zeros(1, 1, self.hidden_dim)))

    def forward(self, sentence):
        embeds = self.word_embeddings(sentence)
        lstm_out, self.hidden = self.lstm(
            embeds.view(len(sentence), 1, -1), self.hidden)
        tag_space = self.hidden2tag(lstm_out.view(len(sentence), -1))
        tag_scores = F.log_softmax(tag_space)
        return tag_scores

######################################################################
# Train the model:


model = LSTMTagger(EMBEDDING_DIM, HIDDEN_DIM, len(word_to_ix), len(tag_to_ix))
loss_function = nn.NLLLoss()
optimizer = optim.SGD(model.parameters(), lr=0.1)

# See what the scores are before training
# Note that element i,j of the output is the score for tag j for word i.
inputs = prepare_sequence(training_data[0][0], word_to_ix)
tag_scores = model(inputs)
print(tag_scores)

for epoch in range(300):  # again, normally you would NOT do 300 epochs, it is toy data
    for sentence, tags in training_data:
        # Step 1. Remember that Pytorch accumulates gradients.
        # We need to clear them out before each instance
        model.zero_grad()

        # Also, we need to clear out the hidden state of the LSTM,
        # detaching it from its history on the last instance.
        model.hidden = model.init_hidden()

        # Step 2. Get our inputs ready for the network, that is, turn them into
        # Variables of word indices.
        sentence_in = prepare_sequence(sentence, word_to_ix)
        targets = prepare_sequence(tags, tag_to_ix)

        # Step 3. Run our forward pass.
        tag_scores = model(sentence_in)

        # Step 4. Compute the loss, gradients, and update the parameters by
        #  calling optimizer.step()
        loss = loss_function(tag_scores, targets)
        loss.backward()
        optimizer.step()

# See what the scores are after training
inputs = prepare_sequence(training_data[0][0], word_to_ix)
tag_scores = model(inputs)
# The sentence is "the dog ate the apple".  i,j corresponds to score for tag j
#  for word i. The predicted tag is the maximum scoring tag.
# Here, we can see the predicted sequence below is 0 1 2 0 1
# since 0 is index of the maximum value of row 1,
# 1 is the index of maximum value of row 2, etc.
# Which is DET NOUN VERB DET NOUN, the correct sequence!
print(tag_scores)


######################################################################
# Exercise: Augmenting the LSTM part-of-speech tagger with character-level features
# To get the character level representation, do an LSTM over the
# characters of a word, and let`c_w` be the final hidden state of
# this LSTM. Hints:
#
# * There are two LSTM's in the new model.
#   The original one that outputs POS tag scores, and the new one that
#   outputs a character-level representation of each word.
# * To do a sequence model over characters, I will have to embed characters.
#   The character embeddings will be the input to the character LSTM.
#

class LSTMTaggerWithChar(nn.Module):
    def __init__(self, embedding_Wdim, embedding_Cdim, hidden_dim, vocab_size, Char_Size, tagset_size):
        super(LSTMTaggerWithChar,self).__init__()
        self.hidden_dimW = hidden_dim
        self.hidden_dimC = embedding_Cdim
        self.word_embedding = nn.Embedding(vocab_size,embedding_Wdim)
        self.char_embedding = nn.Embedding(Char_Size,embedding_Cdim)
        self.lstmC = nn.LSTM(embedding_Cdim, embedding_Cdim)
        self.lstmW = nn.LSTM(embedding_Wdim+embedding_Cdim, hidden_dim)
        self.hidden2tag = nn.Linear(hidden_dim, tagset_size)
        self.hiddenW = self.init_hiddenW()
        self.hiddenC = self.init_hiddenC()
        
    def init_hiddenW(self):
        return(autograd.Variable(torch.zeros(1,1,self.hidden_dimW)),
               autograd.Variable(torch.zeros(1,1,self.hidden_dimW)))
        
    def init_hiddenC(self):
        return(autograd.Variable(torch.zeros(1,1,self.hidden_dimC)),
               autograd.Variable(torch.zeros(1,1,self.hidden_dimC)))
    
    def forward(self,inputs_W, inputs_C):
        Wembeds = self.word_embedding(inputs_W)
        ListWCs = []
        for i in range(len(inputs_C)):
            VarIinputs_C = autograd.Variable(torch.LongTensor(inputs_C[i]))
            Cembeds = self.char_embedding(VarIinputs_C)
            _,self.hiddenC = self.lstmC(
                    Cembeds.view(len(inputs_C[i]),1,-1),self.hiddenC)
            ListWCs.append(self.hiddenC[0])
        ListWCs = torch.cat(ListWCs).view(len(Wembeds),-1)
        NewWembeds = torch.cat((Wembeds,ListWCs),1)
        lstm_out,self.hiddenW = self.lstmW(
                NewWembeds.view(len(inputs_W),1,-1),self.hiddenW)
        
        tag_space = self.hidden2tag(lstm_out.view(len(inputs_W),-1))
        tag_scores = F.log_softmax(tag_space)
        return tag_scores
    
EMBEDDING_WDIM = 6
EMBEDDING_CDIM = 6
HIDDEN_DIM = 6

import string
Alphabet = list(string.ascii_letters)
Char_Size = len(Alphabet)
Char_to_ix = {ch:i for i,ch in enumerate(Alphabet)}

def prepare_char_squence(seq, to_ix):
    WordCList = []
    for word in seq:
        idxs = [to_ix[ch] for ch in word]
        WordCList.append(idxs)
    return WordCList
    
model2 = LSTMTaggerWithChar(EMBEDDING_WDIM,EMBEDDING_CDIM,HIDDEN_DIM,len(word_to_ix),Char_Size,len(tag_to_ix))
loss_function = nn.NLLLoss()
optimizer = optim.SGD(model2.parameters(), lr=0.1)
inputs_W = prepare_sequence(training_data[0][0], word_to_ix)
inputs_C = prepare_char_squence(training_data[0][0], Char_to_ix)
tag_scores = model2(inputs_W,inputs_C)
print(tag_scores)

for epoch in range(300):
    for sent,tags in training_data:
        model2.zero_grad()
        model2.hiddenC = model2.init_hiddenC()
        model2.hiddenW = model2.init_hiddenW()
        inputs_W = prepare_sequence(sent,word_to_ix)
        inputs_C = prepare_char_squence(sent,Char_to_ix)
        targets = prepare_sequence(tags,tag_to_ix)
        
        tag_scores = model2(inputs_W,inputs_C)
        loss = loss_function(tag_scores,targets)
        loss.backward()
        optimizer.step()

inputs_W = prepare_sequence(training_data[0][0], word_to_ix)
inputs_C = prepare_char_squence(training_data[0][0], Char_to_ix)
tag_scores = model2(inputs_W,inputs_C)
print(tag_scores)        