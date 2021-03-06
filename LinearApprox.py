import numpy as np
from scipy.optimize import nnls
from scipy.linalg import lstsq
import bpy
import math
import copy

#declare object name to save appropiatelly
maxFrames = None
maxBones = None
objName = None
fileName = None
outputName = None

#the blender home directory is needed for the project (eg: C:\\Users\\----\\Blender)
blenderHomeDir = ""

#which verts to be calculate weights and bones for (-1,-1 for all)
# vertsDebug = [1804,1862]
vertsDebug = [-1,-1]


#fills empty array with global vertData of frame
def getVerts(realVertData, frame):
    realVerts = open(blenderHomeDir+"\\globalVertices\\"+fileName+"\\vert"+str(frame)+".txt")

    #getting global vert data
    for pos,line in enumerate(realVerts):
        if(pos>vertsDebug[0]):
            tmpArr = line.split(",")
            vx = float(tmpArr[0])
            vy = float(tmpArr[1])
            vz = float(tmpArr[2])
            realVertData.append(np.array([vx,vy,vz]))
        if(pos==vertsDebug[1]):
            break

#returns array with vertex coords in certain frame        
def getFrameVert(frame, vert):
    realVerts = open(blenderHomeDir+"\\globalVertices\\"+fileName+"\\vert"+str(frame)+".txt")
    #getting global vert data
    for pos,line in enumerate(realVerts):
        if(pos==vert):
            tmpArr = line.split(",")
            vx = float(tmpArr[0])
            vy = float(tmpArr[1])
            vz = float(tmpArr[2])
            return [vx, vy, vz]
        
        
#get restPose vertices
restVerts = open(blenderHomeDir+"\\restPoseVerts\\"+fileName+"\\verts.txt")
restVertData = []
for pos,line in enumerate(restVerts):
    if(pos>vertsDebug[0]):
        tmpArr = line.split(",")
        vx = float(tmpArr[0])
        vy = float(tmpArr[1])
        vz = float(tmpArr[2])
        restVertData.append(np.array([vx,vy,vz,1.]))
    if(pos==vertsDebug[1]):
        break
    

#initialize (1.) random weights in (0,1) with coefficency
def randomWeights():
    weightFile = open(blenderHomeDir+"\\weights\\"+fileName+"\\weights.txt")
    weights = [] 
    vertexGroups = []
    for p,l in enumerate(weightFile):
        if(p>vertsDebug[0]):
            vertGroups = l[1:l.find(']')].split(',')
            w = []
            for i in range(len(vertGroups)):
                vertGroups[i] = int(vertGroups[i])
                w.append(np.random.rand(1,1)[0,0])
            sumw = sum(w)
            for i in range(len(w)):
                w[i] = w[i]/sumw
            vertexGroups.append(vertGroups)  
            weights.append(w)
        if(p==vertsDebug[1]):
            break
    weightFile.close()
    return weights, vertexGroups
    
#init (3.) correct weight initialization
def correctWeights():
    weightFile = open(blenderHomeDir+"\\weights\\"+fileName+"\\weights.txt")
    weights = [] 
    vertexGroups = []
    for p,l in enumerate(weightFile):
        if(p>vertsDebug[0]):
            vertGroups = l[1:l.find(']')].split(',')
            w = []
            for i in range(len(vertGroups)):
                vertGroups[i] = int(vertGroups[i])
            weight = l[l.find(']')+4:(len(l)-2)].split(',')
            w = np.array([])
            for i in weight:
                w = np.append(w,float(i))
            vertexGroups.append(vertGroups)  
            weights.append(w)
        if(p==vertsDebug[1]):
            break
    weightFile.close()
    return weights, vertexGroups

#init weights for init1 and vertexGroups in bones array
weights, vertexGroups = randomWeights()
bones = []
for i in vertexGroups:
    for j in i:
        if j not in bones:
            bones.append(j)
bones.sort()



#init b matrix of verts for bone lienar approximation
b = []
for frame in range(1,maxFrames):
    b.append([])
    realVertData = []
    getVerts(realVertData, frame)
    for v in realVertData:
        b[frame-1].append(v[0]) #vix
        b[frame-1].append(v[1]) #viy
        b[frame-1].append(v[2]) #viz 

#init A matrix for bone linear approximation
def initAboneMats(weightList, vertexGroups):
    cc = 0 # vertex counter to get ccorresponding weights
    A = []
    for v in restVertData:
        tmp = []
        tmp1 = []
        tmp2 = []
        weightIndex = 0
        for vg in bones:
            if(vg in vertexGroups[cc]):
                for i in range(0,4):
                    tmp.append(weightList[cc][weightIndex] * v[i])
                    tmp1.append(0.)
                    tmp2.append(0.)
                for i in range(0,4):
                    tmp.append(0.)
                    tmp1.append(weightList[cc][weightIndex] * v[i])
                    tmp2.append(0.)
                for i in range(0,4):
                    tmp.append(0.)
                    tmp1.append(0.)
                    tmp2.append(weightList[cc][weightIndex] * v[i])
                weightIndex += 1
            else:
                for i in range(0,12):
                    tmp.append(0.)
                    tmp1.append(0.)
                    tmp2.append(0.)
        A.append(tmp)
        A.append(tmp1)
        A.append(tmp2)
        cc += 1
    return A

#linear system with least square method for approximation of joint transformation matrices
def fitBones(weightList, vertexGroups):
    boneTransforms = []
    AboneMats = initAboneMats(weightList, vertexGroups)
    for frame in range(1,maxFrames):
        linearSquare = np.linalg.lstsq(AboneMats,b[frame-1], rcond = -1)
        boneTransforms.append(linearSquare[0])
    return boneTransforms
    
#we solve non negative lienar system with least squares for the weights approximation
def fitWeights(boneMat, vertexGroups):
    newWeights = []
    vv = 0
    actualVV = 0
    if(vertsDebug[0]>0):
        actualVV = vertsDebug[0]+1
    for v in restVertData:
        AA = np.zeros(((3*(maxFrames-1))+1 , maxBones), float)
        bb = []
        for frame in range(1,maxFrames):
            for i in getFrameVert(frame, actualVV):
                bb.append(i)
            for i in range(0,maxBones):
                if(i<len(vertexGroups[vv])):
                    bonePos = 12*bones.index(vertexGroups[vv][i])
                    lines = [[],[],[]]
                    for j in range(0,4):
                        lines[0].append(boneMat[frame-1][bonePos+j])
                        lines[1].append(boneMat[frame-1][bonePos+j+4])
                        lines[2].append(boneMat[frame-1][bonePos+j+8])
                    AA[3*(frame-1)][i] = np.array(lines[0]) @ v
                    AA[3*(frame-1) + 1][i] = np.array(lines[1]) @ v
                    AA[3*(frame-1) + 2][i] = np.array(lines[2]) @ v
                else:
                    break   
        # the last rows of bb and AA are for convex effic weithgts = 1
        bb.append(1.)
        for i in range(0,maxBones):
            if(i<len(vertexGroups[vv])):
                AA[len(AA)-1][i] = 1.
        tmpWeights = nnls(AA,bb)[0]
        newWeights.append(tmpWeights)  
        vv += 1 
        actualVV += 1 
    return newWeights
    
#function to save results in file
def printResults(weightList, boneMats, mode, vertexGroups):
    for i in range(len(weightList)):
        sumWi = sum(weightList[i])
        if(np.isnan(weightList[i][0])):
            print(i,mode)
            weightList[i][0] = 1.
        else:
            for j in range(len(weightList[i])):
                weightList[i][j] = weightList[i][j] / sumWi
    with open(blenderHomeDir+"\\approxWeights\\"+outputName+"\\"+mode+"\\approxVertWeights.txt", "w") as weightOutput:
        vv = 0
        for line in weightList:
            tmpString = ""
            for i in range(len(vertexGroups[vv])):
                tmpString += str(line[i]) + ", "
            weightOutput.write(tmpString[:-2] + "\n")
            vv += 1
    for frame in range(1,maxFrames):
        with open(blenderHomeDir+"\\approx\\"+outputName+"\\"+mode+"\\frame"+str(frame)+".txt", "w") as boneOutput:
            lineBreakC = 0
            for j in range(0,int(len(boneMats[frame-1])/4)+1):
                boneOutput.write(str(boneMats[frame-1][4*j:(4*j)+4])[1:-1])
                boneOutput.write("\n")
                lineBreakC += 1
                if(lineBreakC == 3):
                    lineBreakC = 0
                    boneOutput.write("\n")

#init2 of correct bone transformation matrices        
def correctBones():
    boneMatrs = []
    restBones = []
    #get rest bones first
    file = open(blenderHomeDir+"\\bones\\"+fileName+"\\restBones.txt")
    all_lines = file.readlines()
    for i in bones:
        tmpRest = np.zeros(shape=(4,4))
        for j in range(4):
            tmpLine = []
            for elem in getBoneData(j,all_lines[(i*5) + j]):
                tmpLine.append(elem)
            tmpRest[j] = tmpLine
        restBones.append(tmpRest)
    file.close()
    for frame in range(1,maxFrames):
        boneMatrs.append([])
        file = open(blenderHomeDir+"\\bones\\"+fileName+"\\bone"+str(frame)+".txt")
        all_lines = file.readlines()
        for i in bones:
            tmpBone = np.zeros(shape=(4,4))
            for j in range(4):
                tmpLine = []
                for elem in getBoneData(j,all_lines[(i*5) + j]):
                    tmpLine.append(elem)
                tmpBone[j] = tmpLine
            #now we multiply rest and actual bone transf
            tmpResult = tmpBone @ restBones[bones.index(i)]
            for k in range(3):
                boneMatrs[frame-1].append(tmpResult[k,0])
                boneMatrs[frame-1].append(tmpResult[k,2] * (-1))
                boneMatrs[frame-1].append(tmpResult[k,1])
                boneMatrs[frame-1].append(tmpResult[k,3])
        file.close()
    return boneMatrs
    
    
#function to get line string from boneFile and transform it into array    
def getBoneData(lineNum, line):
    if "(((" in line:
        firstParen = line.find('(((') + 2
    else:
        firstParen = line.find('(')
    lastParen = line.find(')')
    return [float(x) for x in line[firstParen+1:lastParen].split(",")]    

#print initial values of weights      
def printInitialWeights(weightList, vertexGroups):
    with open(blenderHomeDir+"\\initialRandomWeights\\"+outputName+"\\Weights.txt", "w") as weightOutput:
        vv = 0
        for line in weightList:
            tmpString = ""
            for i in range(len(vertexGroups[vv])):
                tmpString += str(line[i]) + ", "
            weightOutput.write(tmpString[:-2] + "\n")
            vv += 1   

#print initial values of bones               
def printInitialBones(boneMats):
    for frame in range(1,maxFrames):
        with open(blenderHomeDir+"\\initialBones\\"+outputName+"\\frame"+str(frame)+".txt", "w") as boneOutput:
            for elem in boneMats[frame-1]:
                boneOutput.write(str(elem) + '\n')
                 
#main
#number of iterations to print results in each
iters = [3,5,8,10,12]

print('init1 ' + fileName)
#init1
mode1 = ['It3_init1','It5_init1','It8_init1','It10_init1','It12_init1']
weights, vertexGroups = randomWeights()
# printInitialWeights(weights, vertexGroups)
for i in range(iters[len(iters)-1]):
    bonesMats = fitBones(weights, vertexGroups)
    # if(i==0):
    #     printInitialBones(bonesMats)
    weights = fitWeights(bonesMats, vertexGroups)
    if(i+1 in iters):
        mode = mode1[iters.index(i+1)]
        printResults(copy.deepcopy(weights), bonesMats, mode, vertexGroups)

print('init2 ' + fileName)
#init2
mode2 = ['It3_init2','It5_init2','It8_init2','It10_init2','It12_init2']
bonesMats = correctBones()
weights = fitWeights(bonesMats, vertexGroups)
for i in range(iters[len(iters)-1]):
   bonesMats = fitBones(weights, vertexGroups)
   weights = fitWeights(bonesMats, vertexGroups)
   if(i+1 in iters):
       mode = mode2[iters.index(i+1)]
       printResults(copy.deepcopy(weights), bonesMats, mode, vertexGroups)

print('init3 ' + fileName)
#init3
mode3 = ['It3_init3','It5_init3','It8_init3','It10_init3','It12_init3']
weights, vertexGroups = correctWeights()
for i in range(iters[len(iters)-1]):
   bonesMats = fitBones(weights, vertexGroups)
   weights = fitWeights(bonesMats, vertexGroups)
   if(i+1 in iters):
       mode = mode3[iters.index(i+1)]
       printResults(copy.deepcopy(weights), bonesMats, mode, vertexGroups)

