#!/usr/local/bin/python3

## phasdetect   : identifies phased siRNA clusters
## Updated      : version-v1.07 24/04/17 
## author       : kakrana@udel.edu

## Copyright (c): 2016, by University of Delaware
##              Contributor : Atul Kakrana
##              Affilation  : Meyers Lab (Donald Danforth Plant Science Center, St. Louis, MO)
##              License copy: Included and found at https://opensource.org/licenses/Artistic-2.0

#### FUNCTIONS ###########################################

import os,sys,subprocess,multiprocessing,time,getpass,shutil,hashlib,datetime,collections,re,argparse
from importlib.machinery import SourceFileLoader
from multiprocessing import Process, Queue, Pool
from subprocess import check_output
import os.path
from os.path import expanduser
# from dedup import dedup_main,dedup_process,dedup_fastatolist,deduplicate,dedup_writer

#### USER SETTINGS ########################################


### Settings file
setFile         = "phasis.set"
memFile         = "phasis.mem"
res_folder      = "phased_%s"   % (datetime.datetime.now().strftime("%m_%d_%H_%M"))
home            = expanduser("~")
phaster_path    = "%s/.phasis" % (home)

## Degradome - Optional ####################################
deg             = 'N'                               ## Use Degradome validation, IF yes enter PARE db in line below
PARE            = 'GuturGu'                         ## If deg = 'Y' then File for degradome analysis

## ADVANCED SETTINGS #######################################
cores           = 0                                 ## 0: Most cores considered as processor pool | 1-INTEGER: Cores to be considered for pool
# nthread         = 3                                 ## Threads perprocess
# server          = "tarkan.ddpsc.org"              ## Server to use to fetch library information and smallRNA libraries
# perl            = "/usr/local/bin/perl_5.18"        ## Josh updated the perl on Tarkan and its not ready yet for PHAS script FORK is missing and somemore modules -Check with Pingchuan help
perl            = "perl"
Local           = 3                                 ## [0]: Files in directory [2]: Get the libs from $ALLDATA with raw reads 
                                                    ## [3] Get library from srna db with reads filtered on number of hits
noiseLimit      = 2
hitsLimit       = 10
#############################################################
#############################################################

parser      = argparse.ArgumentParser()
parser.add_argument('--lowmem', action='store_true', default=True, help=
    'Flag to reduce memory usage for large genomes. Using this flag'\
    'will increase the runtime for phaser')

args = parser.parse_args()

def checkUser():
    '''
    Checks if user is authorized to use script
    '''
    print ("\n#### Checking user ###########################")
    auser = getpass.getuser()
    print("Hello '%s' - Please report issues at: https://github.com/atulkakrana/PHASIS/issues" % (auser))
    # if auser in allowedUser:
    #     print("Hello '%s' - Issues need to be reproted: https://github.com/atulkakrana/phasTER/issues \n" % (auser))
    # else:
    #     print("YOU ARE NOT AUTHORIZED TO USE DEVELOPMENTAL VERSION OF 'PHASER'")
    #     print("Contact 'Atul Kakrana' at kakrana@gmail.com for permission\n")
    #     sys.exit()
    
    return None

def checkHost(allowedHost):

    '''
    Checks if Phster is allowed at this server
    '''
    print ("#### Pre-run checks ###########################")
    f = subprocess.Popen("hostname", stdout=subprocess.PIPE,shell= True)
    output,err = f.communicate()
    #print (output.decode("ascii"))
    
    host = output.decode("ascii")
    print ('--Current host:',host.strip('\n'))
    
    ## DO not turn OFF this 'for' loop as that given an error while matching current host with allowedHost - Reason Unknown
    # print ('Allowed Hosts:')
    # for host in allowedHost:
    #     print (host)
    print("--Allowed hosts: %s" % (','.join(x for x in allowedHost)))
    
    
    if str(host.strip('\n')) in allowedHost:
        print("--PHASIS is supported on this server - good to go!!!\n")
        pass
    
    else:
        print("--PHASIS is not tested on this server")
        print("--Run your analysis at any of these servers:%s" % (','.join(x for x in allowedHost)))
        print("--Script will exit now\n")
        sys.exit()

    return None

def checkDependency():
    '''Checks for required components on user system'''

    print("\n#### Fn: checkLibs ###########################")
    
    goSignal  = True ### Signal to process is set to true 

    ### Check PYTHON version
    pythonver = sys.version_info[0]
    if int(pythonver) >= 3:
        print("--Python v3.0 or higher          : found")
        pass
    else:
        print("--Python v3.0 or higher          : missing")
        goSignal    = False
        # print("See README for how to INSTALL")

    ### Check PERL version
    # perlver = os.system("perl -e 'print $];' &> /dev/null")
    aninfo  = check_output(["perl", "-v"]).decode("utf-8")
    aninfo2 = aninfo.split('\n')[1].split('(')[1].split(')')[0].rsplit('.',1)[0]
    perlver = aninfo2[1:] ## Remove 'v' before version
    if float(perlver) >= 5.014:
        print("--Perl v5.14 or higher           : found")
        pass
    else:
        print("--Perl v5.14 or higher           : missing")
        goSignal    = False
        # print("See README for how to INSTALL")

    ### Check BOWTIE
    isbowtie = shutil.which("bowtie")
    if isbowtie:
        print("--Bowtie (v1)                    : found")
        pass
    else:
        print("--Bowtie (v1)                    : missing")
        goSignal    = False
        # print("See README for how to INSTALL")

    ### Check Perl dependecies
    retcode = os.system("perl -MScalar::Util -e1 &> /dev/null")
    if retcode == 0:
        print("--Scalar::Util (perl)            : found")
        pass
    else:
        print("--Scalar::Util (perl)            : missing")
        goSignal    = False
        # print("See README for how to INSTALL")

    ### Check Perl dependecies
    retcode = os.system("perl -MData::Dumper -e1 &> /dev/null")
    if retcode == 0:
        print("--Data::Dumper (perl)            : found")
        pass
    else:
        print("--Data::Dumper (perl)            : missing")
        goSignal    = False
        # print("See README for how to INSTALL")

    ### Check Perl dependecies
    retcode = os.system("perl -MParallel::ForkManager -e1 &> /dev/null")
    if retcode == 0:
        print("--Parallel::ForkManager (perl)   : found")
        pass
    else:
        print("--Parallel::ForkManager (perl)   : missing")
        goSignal    = False
        # print("See README for how to INSTALL")

    ### Check Perl dependecies
    retcode = os.system("perl -MGetopt::Long -e1 &> /dev/null")
    if retcode == 0:
        print("--Getopt::Long (perl)            : found")
        pass
    else:
        print("--Getopt::Long (perl)            : missing")
        goSignal    = False
        # print("See README for how to INSTALL")

    if goSignal == False:
        print("\n** Please install the missing libraries before running the analyses")
        # print("See README for how to install these")
        print("** revFerno has unmet dependendies and will exit for now\n")
        sys.exit()

    return None

def readSet(setFile):
    '''
    Read and parse external settings file
    '''

    if os.path.isfile(setFile):
        pass
    else:
        print("---Settings file 'phasis.set' not found in current directory")
        print("---Please copy it to same directory as script and rerun")
        sys.exit()

    print("\n#### Fn: Settings Reader #####################")
    
    fh_in   = open(setFile, 'r')
    setFile = fh_in.readlines()
    fh_in.close()
    
    for line in setFile:
        if line: ## Not empty
            if line.startswith('@'):
                line = line.strip("\n")
                # print(line)
                akey,aval = line.split('=')
                param = akey.strip()
                value = aval.strip()
                # print(param,value)
                
                ### Extract values ######### 
                if param.strip() == '@runType':
                    global runType
                    runType = str(value.strip())
                    if (runType != "G") and (runType != "T") and (runType != "S"):
                        print("Please input correct setting for '@runType' parameter in 'phasis.set' file")
                        print("Script will exit for now\n")
                        sys.exit()
                    else:
                        print('User Input runType               :',runType)

                elif param.strip() == '@reference':
                    global reference
                    reference = str(value.strip())
                    print('User Input reference location    :',reference)
                
                elif param.strip() == '@index':
                    global index
                    index = str(value.strip())
                    if index:
                        print('User Input index location        :',index)
                    else:
                        print('User Input index location        : None')

                elif param.strip() == '@userLibs':
                    global libs
                    # libs = list(map(str,value.strip().split(',')))
                    libs     = [str(x) for x in value.strip().split(',') if x.strip() != '' ] ## This is my dope...
                    print('User Input Libs                  :',",".join(libs))

                elif param.strip() == '@libFormat':
                    global libFormat
                    libFormat = str(value.strip())
                    if (libFormat != "T") and (libFormat != "F"):
                        print("Please input correct setting for '@libFormat' parameter in 'phasis.set' file")
                        print("Script will exit for now\n")
                        sys.exit()
                    else:
                        print('user library format              :',libFormat)

                elif param.strip() == '@phase':
                    global phase
                    phase = int(value.strip())
                    print('User Input for phase length      :',phase)
                
                elif param.strip() == '@path_prepro_git':
                    global phaster_path
                    phaster_path = str(value.strip()).rstrip("/")+"/phaster"
                    # phaster_path = str(value.strip()).rstrip("/")+"/core"
                    print('User Input for phaster path      :',phaster_path)

                elif param.strip() == '@minDepth':
                    global minDepth
                    minDepth = int(value.strip())
                    if not minDepth:
                        minDepth = 3
                    print('User Input for min. sRNA depth   :',minDepth)

                elif param.strip() == '@clustBuffer':
                    global clustBuffer
                    clustBuffer = int(value.strip())
                    if not clustBuffer:
                        clustBuffer = 250
                    print('User Input distance b/w clusters :',clustBuffer)

                # elif param.strip() == '@mismat':
                #     global mismat
                #     mismat = int(value.strip())
                #     if not mismat:
                #         mismat = 0
                #     print('User Input for max mismatches    :',mismat)

            else:
                #print("Missed line:",line)
                pass
    
    # sys.exit()
    return libs

def PHASBatch(con,libs,runType,index,deg):
    '''
    ## Deprecated
    '''
    
    #os.mkdir('./%s' % (lib))
    #output_path = './%s' % (lib)
    
    for lib in libs:
        print (lib)
        cur = con.cursor()
        cur.execute('SELECT processed_path FROM master.library_info where lib_id = %s' % (lib))
        path = cur.fetchall()
        #print(path[0][0])
        
        pro_file    = path[0][0].replace('$ALLDATA', '/alldata')###Processed sRNA file
        out_file    = '%s.txt' % (lib)
        rl          = str(phase)
        nproc2      = str(nproc)
        sRNAratio   = str(75)
        print (pro_file)
        
        if runType == 'G': ### Uses Whole genome as input
            if deg == 'Y':
                retcode = subprocess.call([perl, "/data2/homes/kakrana/svn/users/kakrana/phasiRNA_prediction_pipeline.ver.genome.pl", "-i", pro_file, "-q", PARE, "-f", "-t", sRNAratio, "-d", index, "-px", out_file, "-rl", rl, "-cpu", nproc2])
            else:
                retcode = subprocess.call([perl, "/data2/homes/kakrana/svn/users/kakrana/phasiRNA_prediction_pipeline.ver.genome.pl", "-i", pro_file,"-f", "-t", sRNAratio, "-d", index, "-px", out_file, "-rl", rl, "-cpu", nproc2])
        
        else: ### Uses FASTA file of genes as input         
            #pipe =subprocess.Popen(["perl5.18", "-v"])
            if deg == 'Y':
                retcode = subprocess.call([perl, "/data2/homes/kakrana/svn/users/kakrana/phasiRNA_prediction_pipeline.ver.MUL.pl", "-i", pro_file, "-q", PARE, "-f", "-t", sRNAratio, "-d", index, "-px", out_file, "-rl", rl, "-cpu", nproc2])
            else:
                retcode = subprocess.call([perl, "/data2/homes/kakrana/svn/users/kakrana/phasiRNA_prediction_pipeline.ver.MUL.pl", "-i", pro_file, "-f", "-t", sRNAratio, "-d", index, "-px", out_file, "-rl", rl, "-cpu", nproc2])
                    
        
        if retcode == 0:
            pass
        else:
            print("Problem with Phasing script - Return code not 0")
            sys.exit()
        
    return lib

def TagAbundanceFile(con,db,libs):
    '''
    ### sRNA Libraries are fetched from server
    '''
    for alib in libs:##For all the libraries
        
        ## Check if file already exsits in directory - This saves a lot of time downloading the same file
        filePath = '%s.fas' % (alib)
        if os.path.isfile(filePath) == False:
            print ('\nPreparing sRNA reads file for library: %s' % (alib[0]))
            #print (lib[0])
            #print ('Caching tag and count information from server for PARE alib %s' % (alib[0]) )
            cur = con.cursor()
            cur.execute("SELECT tag,norm from %s.run_master where lib_id = %s AND (hits between 0 and 20)" % (db,alib[0]))
            lib_info = cur.fetchall()
            #print('These are the tags:',lib_info[:10])
            
            fh_out = open('%s.fas' % (alib), 'w')##Naming file with lib_ids name
            print ('Library cached, writing abundance file')
            tag_num = 1
            for ent in lib_info:## All the PARE tags in a library
                #print (ent)
                fh_out.write('%s\t%s\n' % (ent[0],ent[1]))
                tag_num += 1
                
            fh_out.close()
        else:
            print('tag abundance file exists for library: %s' % (alib))
            pass

def PHASBatch2(aninput):
    '''
    Phasing anlysis - New
    '''

    print ("\n#### Fn: phaser #############################")
    # print("\naninput\n",aninput)
    lib,runType,index,deg,nthread,noiseLimit,hitsLimit,clustBuffer = aninput
    
    ### Sanity check #####################
    if not os.path.isfile(lib):
        print("** %s - sRNA library file not found" % (lib))
        print("** Please check the library- Is it in specified directory? Did you input wrong name?")
        print("** Script will exit for now\n")
        sys.exit()
    else:
        print("sRNA library located - Running phasing analysis")
        pass
    #####################################


    pro_file    = lib ### sRNA input file 
    out_file    = './%s/%s.txt' % (res_folder,lib.rpartition(".")[0]) ## Output file suffix
    
    rl          = str(phase)
    # nproc2 = str(nproc)
    nthread     = str(nthread)
    sRNAratio   = str(75)
    noiseLimit  = str(minDepth-1)
    # mismat      = str(mismat)
    clustBuffer = str(clustBuffer)
    print(pro_file)

    if runType == 'G':### Uses Whole genome as input
        full_path = "%s/phasclust.genome.v2.pl" % (phaster_path)
        # print(full_path)
        if deg == 'Y':
            retcode = subprocess.call([perl, "%s/phasclust.genome.v2.pl" % (phaster_path), "-i", pro_file, "-q", PARE, "-f", "-t", sRNAratio, "-d", index, "-px", out_file, "-rl", rl, "-cpu", nthread])
        else:
            if libFormat == "T":
                aformat = "t"
                retcode = subprocess.call([perl, "%s/phasclust.genome.v2.pl" % (phaster_path), "-i", pro_file,"-f", aformat, "-t", sRNAratio,"-n", noiseLimit, "-g", clustBuffer, "-d", index, "-px", out_file, "-rl", rl, "-cpu", nthread])
            elif libFormat == "F":
                aformat = "f"
                retcode = subprocess.call([perl, "%s/phasclust.genome.v2.pl" % (phaster_path), "-i", pro_file,"-f", aformat, "-t", sRNAratio,"-n", noiseLimit, "-g", clustBuffer, "-d", index, "-px", out_file, "-rl", rl, "-cpu", nthread])
            else:
                print("** Invalid '@libFormat' parameter value")
                print("** Please check the '@libFormat' parameter value in setting file")
                print("** F for FASTA format | T for tag-count format are the only acceptable values")
                print("** Script will exit now")
                sys.exit()
    
    else: ### Uses FASTA file of genes as input
        full_path = "%s/phasclust.MUL.v2.pl" % (phaster_path)
        # print(full_path)        
        if deg == 'Y':
            retcode = subprocess.call([perl, "%s/phasclust.MUL.v2.pl" % (phaster_path), "-i", pro_file, "-q", PARE, "-f", "-t", sRNAratio, "-d", index, "-px", out_file, "-rl", rl, "-cpu", nthread])
        else:   
            if libFormat == "T":
                aformat = "t"
                retcode = subprocess.call([perl, "%s/phasclust.MUL.v2.pl" % (phaster_path), "-i", pro_file, "-f", aformat, "-t", sRNAratio,"-n", noiseLimit, "-g", clustBuffer, "-d", index, "-px", out_file, "-rl", rl, "-cpu", nthread])
            elif libFormat == "F":
                aformat = "f"
                retcode = subprocess.call([perl, "%s/phasclust.MUL.v2.pl" % (phaster_path), "-i", pro_file,"-f", aformat, "-t", sRNAratio,"-n", noiseLimit, "-g", clustBuffer, "-d", index, "-px", out_file, "-rl", rl, "-cpu", nthread])
            else:
                print("** Invalid '@libFormat' parameter value")
                print("** Please check the '@libFormat' parameter value in setting file")
                print("** F for FASTA format | T for tag-count format are the only acceptable values")
                print("** Script will exit now")
                sys.exit()

    if retcode == 0:
        pass
    else:
        print("** Problem with Phasing script - Return code not 0")
        sys.exit()
        
    return None

def PP(module,alist):
    '''
    paralleizes process with no results catching
    '''
    start = time.time()
    npool = Pool(int(nproc))
    npool.map(module, alist)

def PPResults(module,alist):
    '''
    Parallelizes and stores result
    '''

    ####
    npool   = Pool(int(nproc))
    res     = npool.map_async(module, alist)
    results = (res.get())
    npool.close()
    return results

def PPBalance(module,alist):
    '''
    Balance process according to core pool
    '''
    #print('***********Parallel instance of %s is being executed*********' % (module))
    start       = time.time()
    ##PP is being used for Bowtie mappings - This will avoid overflooding of processes to server
    nprocPP     = round((nproc/int(nthread))) 
    if nprocPP  < 1:
        nprocPP = 1 ## 1 here so as to avoid 0 processor being allocated in serial mode
    else:
        pass

    print("nprocPP                          : %s" % (nprocPP))
    npool = Pool(int(nprocPP))
    npool.map(module, alist)

def optimize(nproc):
    '''
    dirty optimization of threads per library
    '''

    nlibs       = len(libs)
    ninstances  = int(nproc/nlibs) ### Number of parallel instances to use
    # print("Libs:%s | nproc:%s | ninstance:%s" % (nlibs,nproc,ninstances))

    if ninstances > 3:
        nthread = ninstances
    else:
        nthread = 3

    print("\n#### %s computing core(s) reserved for analysis ##########" % (str(nproc)))
    print("#### %s computing core(s) assigned to one lib ############\n" % (str(nthread)))
    # time.sleep(1)


    return nthread 

def inputList(libs,runType,index,deg,nthread,noiseLimit,hitsLimit,clustBuffer):
    '''generate raw inputs for parallel processing'''

    rawInputs = [] ## An empty list to store inputs for PP
    for alib in libs:
        rawInputs.append((alib,runType,index,deg,nthread,noiseLimit,hitsLimit,clustBuffer))

    # print("These are rawInputs:",rawInputs)

    return rawInputs

def indexBuilder(reference):
    '''
    Generic index building module
    '''
       
    print ("\n#### Fn: indexBuilder #######################")
    ### Sanity check #####################
    if not os.path.isfile(reference):
        print("'%s' reference file not found" % (reference))
        print("Please check the genomeFile - Is it in specified directory? Did you input wrong name?")
        print("Script will exit for now\n")
        sys.exit()
    else:
        print("Reference file located - Preparing to create index")
        pass
    #####################################

    ### Clean reference ################
    fastaclean,fastasumm = FASTAClean(reference,0)

    ### Prepare Index ##################
    print ("**Deleting old index 'folder' !!!!!!!!!!!**")
    shutil.rmtree('./index', ignore_errors=True)
    os.mkdir('./index')
    
    genoIndex   = '%s/index/%s' % (os.getcwd(),fastaclean.rpartition('/')[-1].rpartition('.')[0]) ## Can be merged with genoIndex from earlier part if we use bowtie2 earlier
    # genoIndex   = './index/%s' % (fastaclean.rpartition('/')[-1].rpartition('.')[0]) ## Alternative approach -Can be merged with genoIndex from earlier part if we use bowtie2 earlier
    print('Creating index of cDNA/genomic sequences:%s**\n' % (genoIndex))
    adcv        = "256"
    divn        = "6"

    ### Run based on input about the memory
    if args.lowmem:
        retcode     = subprocess.call(["bowtie-build","-f", fastaclean, genoIndex])
    else:
        retcode     = subprocess.call(["bowtie-build","-f", "--noauto", "--dcv", adcv,"--bmaxdivn", divn, fastaclean, genoIndex])
    
    if retcode == 0:## The bowtie mapping exit with status 0, all is well
        # print("Reference index prepared sucessfully")
        pass
    else:
        print("There is some problem preparing index of reference '%s'" %  (reference))
        print("Is 'Bowtie' installed? And added to environment variable?")
        print("Script will exit now")
        sys.exit()
    ##########################################

    ## Test for index files #################
    # Close this code if not testing
    # fh_in1 = open("./index/Triticum_aestivum.TGACv1.dna.toplevel.clean.1.ebwtl",'w')
    # fh_in1.write("Atul is a developer for PHASIS")
    # fh_in1.close()
    ##########################################

    ### Make a memory file ###################
    fh_out      = open(memFile,'w')
    # print("Generating MD5 hash for reference")
    refHash     = (hashlib.md5(open('%s' % (reference),'rb').read()).hexdigest()) ### reference hash used instead of cleaned FASTA because while comparing only the user input reference is available
    
    print("Generating MD5 hash for Bowtie index")
    if os.path.isfile("%s.1.ebwtl" % (genoIndex)):
        indexHash   = (hashlib.md5(open('%s.1.ebwtl' % (genoIndex),'rb').read()).hexdigest())
    elif os.path.isfile("%s.1.ebwt" % (genoIndex)):
        indexHash   = (hashlib.md5(open('%s.1.ebwt' % (genoIndex),'rb').read()).hexdigest())
    else:
        print("File extension for index couldn't be determined properly")
        print("It could be an issue from Bowtie")
        print("This needs to be reported to 'PHASIS' developer - Script will exit")
        sys.exit()

    print("\n@genomehash:%s | @indexhash:%s" % (refHash, indexHash) )
    fh_out.write("@timestamp:%s\n" % (datetime.datetime.now().strftime("%m_%d_%H_%M")))
    fh_out.write("@genomehash:%s\n" % (refHash))
    fh_out.write("@index:%s\n" % (genoIndex))
    fh_out.write("@indexhash:%s\n" % (indexHash))

    print("Index prepared:%s\n" % (genoIndex))

    # sys.exit()
    
    return genoIndex

def indexBuilder2(reference,fastaclean):
    '''
    Prepared to work with parallelized version of FASTA cleaner - Not implemented yet - because parallel FASTA
    cleaner is slow on bigger genomes - need trouble shooting
    '''
    
    
    print ("\n#### Fn: indexBuilder #######################")

    ### Prepare Index ##################
    print ("**Deleting old index 'folder' !!!!!!!!!!!**")
    shutil.rmtree('./index', ignore_errors=True)
    os.mkdir('./index')
    
    genoIndex   = '%s/index/%s' % (os.getcwd(),fastaclean.rpartition('/')[-1].rpartition('.')[0]) ## Can be merged with genoIndex from earlier part if we use bowtie2 earlier
    # genoIndex   = './index/%s' % (fastaclean.rpartition('/')[-1].rpartition('.')[0]) ## Alternative approach -Can be merged with genoIndex from earlier part if we use bowtie2 earlier
    print('Creating index of cDNA/genomic sequences:%s**\n' % (genoIndex))
    adcv        = "256"
    divn        = "6"

    ### Run based on input about the memory
    if args.lowmem:
        retcode     = subprocess.call(["bowtie-build","-f", fastaclean, genoIndex])
    else:
        retcode     = subprocess.call(["bowtie-build","-f", "--noauto", "--dcv", adcv,"--bmaxdivn", divn, fastaclean, genoIndex])
    
    if retcode == 0:## The bowtie mapping exit with status 0, all is well
        # print("Reference index prepared sucessfully")
        pass
    else:
        print("There is some problem preparing index of reference '%s'" %  (reference))
        print("Is 'Bowtie' installed? And added to environment variable?")
        print("Script will exit now")
        sys.exit()
    ##########################################

    ### Test for index files #################
    # ## Close this code if not testing
    # fh_in1 = open("./index/Triticum_aestivum.TGACv1.dna.toplevel.clean.1.ebwtl",'w')
    # fh_in1.write("Atul is a developer for PHASIS")
    # fh_in1.close()
    ##########################################

    ### Make a memory file ###################
    fh_out      = open(memFile,'w')
    print("Generating MD5 hash for reference")
    refHash     = (hashlib.md5(open('%s' % (reference),'rb').read()).hexdigest()) ### reference hash used instead of cleaned FASTA because while comparing only the user input reference is available
    
    print("Generating MD5 hash for Bowtie index")
    if os.path.isfile("%s.1.ebwtl" % (genoIndex)):
        indexHash   = (hashlib.md5(open('%s.1.ebwtl' % (genoIndex),'rb').read()).hexdigest())
    elif os.path.isfile("%s.1.ebwt" % (genoIndex)):
        indexHash   = (hashlib.md5(open('%s.1.ebwt' % (genoIndex),'rb').read()).hexdigest())
    else:
        print("File extension for index couldn't be determined properly")
        print("It could be an issue from Bowtie")
        print("This needs to be reported to 'PHASIS' developer - Script will exit")
        sys.exit()

    print("\n@genomehash:%s | @indexhash:%s" % (refHash, indexHash) )
    fh_out.write("@timestamp:%s\n" % (datetime.datetime.now().strftime("%m_%d_%H_%M")))
    fh_out.write("@genomehash:%s\n" % (refHash))
    fh_out.write("@index:%s\n" % (genoIndex))
    fh_out.write("@indexhash:%s\n" % (indexHash))

    print("Index prepared:%s\n" % (genoIndex))

    # sys.exit()
    
    return genoIndex

def indexIntegrityCheck(index):
    '''
    Checks the integrity of index and the extension
    '''
    indexFolder     = index.rpartition("/")[0]
    # print("This is the folder from earlier run:%s" % (indexFolder))
    if os.path.isfile("%s.1.ebwtl" % (index)): ## Check if this extension exists in folder
        indexExt    = "ebwtl"
        indexFiles  = [i for i in os.listdir('%s' % (indexFolder)) if i.endswith('.ebwtl')]
        if len(indexFiles) >= 6:
            # print("Index has all six parts")
            indexIntegrity = True

    elif os.path.isfile("%s.1.ebwt" % (index)):
        indexExt    = "ebwt"
        indexFiles  = [i for i in os.listdir('%s' % (indexFolder)) if i.endswith('.ebwt')]
        if len(indexFiles) >= 6:
            # print("Index has all six parts")
            indexIntegrity = True
    else:
        print("Existing index extension couldn't be determined")
        print("Genome index will be remade")
        indexExt        = False
        indexIntegrity  = False

    print("Ancillary data integrity         :",indexIntegrity)
    # print("Number of files:%s" % (len(indexFiles)))

    return indexIntegrity,indexExt

def FASTAClean(filename,mode):
    
    '''Cleans FASTA file - multi-line fasta to single line, header clean, empty lines removal'''

    ## Read seqeunce file
    fh_in       = open(filename, 'r')
    print ("phasdetect uses FASTA header as key for identifying the phased loci")
    print ("Caching '%s' reference FASTA file" % (filename))
    
    ## Write file
    if mode == 0:
        fastaclean = ('%s/%s.clean.fa' % (os.getcwd(),filename.rpartition('/')[-1].rpartition('.')[0])) ## os.getcwd(),fastaclean.rpartition('/')[-1].rpartition('.')[0]
    else:
        print("Input correct mode- 0: Normal | 1: Seqeunces reversed | 2: Seqeunces reverse complemented | 3: Seqeunces complemented only")
        print("USAGE: cleanFasta.v.x.x.py FASTAFILE MODE")
        sys.exit()

    ### Outfiles
    fh_out1     = open(fastaclean, 'w')
    fastasumm   = ('%s/%s.summ.txt' % (os.getcwd(),filename.rpartition('/')[-1].rpartition('.')[0]))
    fh_out2     = open(fastasumm, 'w')
    fh_out2.write("Name\tLen\n")
    
    ### Read files
    fasta       = fh_in.read()
    fasta_splt  = fasta.split('>')

    fastaD      = {}    ## Store FASTA as dict
    acount      = 0     ## count the number of entries
    empty_count = 0
    for i in fasta_splt[1:]:
        ent     = i.split('\n')
        aname   = ent[0].split()[0].strip()
        
        if runType == 'G':
            ## To match with phasing-core script for genome version which removed non-numeric and preceding 0s
            name = re.sub("[^0-9]", "", aname).lstrip('0')
        else:
            name = aname
        
        seq     = ''.join(x.strip() for x in ent[1:]) ## Sequence in multiple lines
        alen    = len(seq)
        if alen > 200:
            fh_out1.write('>%s\n%s\n' % (name,seq))
            fh_out2.write('%s\t%s\n' % (name,alen))
            acount+=1
        else:
            empty_count+=1
            pass

    #### Prepare a dictionary - Not Tested
    # for line in fh_in:
    #     if line.startswith('>'):
    #       name          = line[1:].rstrip('\n').split()[0]
    #       fastaD[name]  = ''
    #     else:
    #       fastaD[name]  += line.rstrip('\n').rstrip('*')

    #### Write results - Not tested
    # for name,seq in fastaD.items():
    #     alen = len(seq)

    #     if alen > 200:
    #         fh_out1.write('>%s\n%s\n' % (name,seq))
    #         fh_out2.write('%s\t%s\n' % (name,alen))
    #         acount+=1
    #     else:
    #         empty_count+=1
    #         pass

    
    fh_in.close()
    fh_out1.close()
    fh_out2.close() 

    print("Fasta file with reduced header: '%s' with total entries %s is prepared" % (fastaclean, acount))
    print("There were %s entries found with empty sequences and were removed\n" % (empty_count))
    
    return fastaclean,fastasumm

def readMem(memFile):
    '''
    Reads memory file and gives global variables
    '''
    print ("#### Fn: memReader ############################")
    fh_in       = open(memFile,'r')
    memRead     = fh_in.readlines()
    fh_in.close()

    memflag     = True
    varcount    = 0 
    for line in memRead:
        if line: ## Not empty
            if line.startswith('@'):
                line        = line.strip("\n")
                # print(line)
                akey,aval   = line.split(':')
                param       = akey.strip()
                value       = aval.strip()
                # print(param,value)

                if param == '@genomehash':
                    global existRefHash
                    varcount+=1
                    existRefHash = str(value)
                    print('Existing reference hash          :',existRefHash)

                elif param == '@indexhash':
                    global existIndexHash
                    varcount+=1
                    existIndexHash = str(value)
                    print('Existing index hash              :',existIndexHash)

                elif param == '@index':
                    global index
                    varcount+=1
                    index = str(value)
                    print('Existing index location          :',index)
                
                else:
                    pass

    ## Sanity Check - Memory file is not empty, from a crash
    # if existRefHash.strip() == '':
    #     memflag = False
    # elif existIndexHash.strip() == '':
    #     memflag = False
    # elif index.strip() == '':
    #     memflag = False

    if varcount == 3:
        memflag = True
    else:
        memflag = False

    return memflag

def coreReserve(cores):
    '''
    Decides the core pool for machine - written to make PHASIS comaptible with machines that 
    have less than 10 cores - Will be improved in future
    '''

    if cores == 0:
        ## Automatic assignment of cores selected
        totalcores = int(multiprocessing.cpu_count())
        if totalcores   == 4: ## For quad core system
            nproc = 3
        elif totalcores == 6: ## For hexa core system
            nproc = 5
        elif totalcores > 6 and totalcores <= 10: ## For octa core system and those with less than 10 cores
            nproc = 7
        else:
            nproc = int(totalcores*0.9)
    else:
        ## Reserve user specifed cores
        nproc = int(cores)

    return nproc

#### FASTA CLEAN P - IN DEV

def FASTAread(filename):
    
    '''
    Reads FASTA file to alist
    '''
    ### Sanity check #####################
    if not os.path.isfile(reference):
        print("'%s' reference file not found" % (reference))
        print("Please check the genomeFile - Is it in specified directory? Did you input wrong name?")
        print("Script will exit for now\n")
        sys.exit()
    else:
        print("Reference file located - Preparing to create index")
        pass
    #####################################

    ### Read seqeunce file ##############
    fh_in       = open(filename, 'r')
    print ("phasdetect uses FASTA header as key for identifying the phased loci")
    print ("Caching reference '%s' FASTA file" % (filename))

    fasta       = fh_in.read()
    fasta_splt  = fasta.split('>')
    print("Cached FASTA file with %s entries" % (len(fasta_splt[1:])))

    fh_in.close()

    return fasta_splt[1:]

def FASTAclean(ent):
    '''
    Cleans one entry of FASTA file - multi-line fasta to single line, header clean, empty lines removal
    '''

    ent_splt    = ent.split('\n')
    aname       = ent_splt[0].split()[0].strip()
    # print("Cleaning - %s" % (aname))
    
    if runType == 'G':
        ## To match with phasing-core script for genome version which removed non-numeric and preceding 0s
        bname = re.sub("[^0-9]", "", aname).lstrip('0')
    else:
        bname = aname
    
    bseq     = ''.join(x.strip() for x in ent[1:]) ## Sequence in multiple lines

    return bname,bseq

def FASTAwrite(filename,alist,mode):
    '''
    Writes list of processed/cleaned FASTA
    '''

    ## Write file
    if mode == 0:
        fastaclean = ('%s/%s.clean.fa' % (os.getcwd(),filename.rpartition('/')[-1].rpartition('.')[0])) ## os.getcwd(),fastaclean.rpartition('/')[-1].rpartition('.')[0]
    else:
        print("Input correct mode- 0: Normal | 1: Seqeunces reversed | 2: Seqeunces reverse complemented | 3: Seqeunces complemented only")
        print("USAGE: cleanFasta.v.x.x.py FASTAFILE MODE")
        sys.exit()

    ### Outfiles
    fh_out1     = open(fastaclean, 'w')
    fastasumm   = ('%s/%s.summ.txt' % (os.getcwd(),filename.rpartition('/')[-1].rpartition('.')[0]))
    fh_out2     = open(fastasumm, 'w')
    fh_out2.write("Name\tLen\n")

    acount      = 0     ## count the number of entries
    empty_count = 0     ## count empty entries
    
    for ent in alist:
        aname,aseq  = ent
        alen        = len(aseq)
    
        if alen > 200:
            fh_out1.write('>%s\n%s\n' % (aname,aseq))
            fh_out2.write('%s\t%s\n' % (aname,alen))
            acount+=1
        else:
            empty_count+=1
            pass


    fh_out1.close()
    fh_out2.close() 

    print("Fasta file with reduced header: '%s' with total entries %s is prepared" % (fastaclean, acount))
    print("There were %s entries with empty/short sequences,these were removed\n" % (empty_count))
    
    return fastaclean,fastasumm

#### DE-DUPLICATOR MODULES ####

def dedup_process(alib):
    '''
    To parallelize the process
    '''
    print("\n#### Fn: De-duplicater #######################")

    afastaL     = dedup_fastatolist(alib)         ## Read
    acounter    = deduplicate(afastaL )            ## De-duplicate
    countFile   = dedup_writer(acounter,alib)   ## Write

    return countFile

def dedup_fastatolist(alib):
    '''
    New FASTA reader
    '''

    ### Sanity check
    try:
        f = open(alib,'r')
    except IOError:                    
        print ("The file, %s, does not exist" % (alib))
        return None


    ## Output 
    fastaL      = [] ## List that holds FASTA tags

    print("Reading FASTA file:%s" % (alib))
    read_start  = time.time()
    
    acount      = 0
    empty_count = 0
    for line in f:
        if line.startswith('>'):
            seq = ''
            pass
        else:
          seq = line.rstrip('\n')
          fastaL.append(seq)
          acount += 1

    read_end    = time.time()
    # print("-- Read time: %ss" % (str(round(read_end-read_start,2))))
    print("Cached file: %s | Tags: %s | Empty headers: %ss" % (alib,acount,empty_count)) 

    return fastaL
                   
def deduplicate(afastaL):
    '''
    De-duplicates tags using multiple threads and libraries using multiple cores
    '''
    dedup_start  = time.time()

    # deList = [] ## Hold deduplicated tags and their abudnaces in a tuple

    acounter    = collections.Counter(afastaL)

    dedup_end  = time.time()
    # print("-- dedup time: %ss" % (str(round(dedup_end-dedup_start,2))))

    return acounter 

def dedup_writer(acounter,alib):
    '''
    writes rtag count to a file
    '''

    print("Writing counts file for %s" % (alib))
    countFile   = "%s.fas" % alib.rpartition('.')[0]  ### Writing in de-duplicated FASTA format as required for phaster-core
    fh_out       = open(countFile,'w')

    acount      = 0
    seqcount    = 1 ## TO name seqeunces
    for i,j in acounter.items():
        # fh_out.write("%s\t%s\n" % (i,j))
        fh_out.write(">seq_%s|%s\n%s\n" % (seqcount,j,i))
        acount      += 1
        seqcount    += 1

    print("Total unique entries written for %s: %s" % (alib,acount))

    fh_out.close()

    return countFile

#### MAIN ###################################################
#############################################################

def main(libs):

    ### Open the runlog
    runLog          = 'runtime_%s' % datetime.datetime.now().strftime("%m_%d_%H_%M")
    fh_run          = open(runLog, 'w')
    phaser_start    = time.time()

    ### 0. Prepare index or reuse old #############
    ###############################################

    ## Did user provided its index? If Yes Skip making memory files
    if not index:
        ### Check genome file and index
        if not os.path.isfile(memFile):
            print("This is first run - create index")
            indexflag = False       ## index will be made on fly
        
        else:
            memflag     = readMem(memFile)
            if memflag  == False:
                print("Memory file is empty - seems like previous run crashed")
                print("Creating index")
                indexflag = False   ## index will be made on fly

            elif memflag  == True:
                ## valid memory file detected - use existing index 
                print("Generating MD5 hash for current reference file")
                currentRefHash = hashlib.md5(open('%s' % (reference),'rb').read()).hexdigest()
                print('Current reference hash           :',currentRefHash)
                
                #### Test #######
                # if os.path.isdir(index.rpartition('/')[0]):
                #     print("There is a folder names 'index'")
                #     pass
                
                # if currentRefHash == existRefHash:
                #     print("current ref. hash is same as exiting ref hash")
                #     pass
                # sys.exit()

                if currentRefHash == existRefHash:
                    # print("Current reference file matches with the earlier run")
                    indexIntegrity,indexExt = indexIntegrityCheck(index)
                    if indexIntegrity:          ### os.path.isdir(index.rpartition('/')[0]):
                        print("Index status                     : Re-use")
                        genoIndex   = index
                        indexflag   = True
                        fh_run.write("Indexing Time: 0s\n")
                    else:
                        print("Index status                     : Re-make")
                        indexflag   = False   ## index will be made on fly
                else:
                    ## Different reference file - index will be remade
                    print("Index status                     : Re-make")
                    indexflag       = False
                    print("Existing index does not matches specified genome - It will be recreated")


        if indexflag == False:
            ## index will be remade

            ## original function - active
            tstart      = time.time()
            genoIndex   = indexBuilder(reference)
            tend        = time.time()
            fh_run.write("Indexing Time:%ss\n" % (round(tend-tstart,2)))

            # ## parallel function - not used - slow on large genomes like wheat due to I/O of data to different cores
            # fastaL                  = FASTAread(reference)
            # ## Test - Serial mode
            # # cleanFasL = []
            # # for ent in fastaL:
            # #     bname,bseq = FASTAclean(ent)
            # #     cleanFasL.append((bname,bseq))
            # cleanFasL               = PPResults(FASTAclean,fastaL)
            # fastaclean,fastasumm    = FASTAwrite(reference,cleanFasL,0)
            # genoIndex               = indexBuilder(reference)
            # tend                    = time.time()
            # fh_run.write("Indexing Time:%ss\n" % (round(tend-tstart,2)))


    else:        
        genoIndex = index
        if not (os.path.isfile("%s.1.ebwt" % (genoIndex)) or os.path.isfile("%s.1.ebwtl" % (genoIndex))) :
            print("** %s - User specified index not found" % (genoIndex))
            print("** Please check the value for @index parameter in settings file")
            print("** Is it in specified directory? Did you input wrong name?")
            print("** Script will exit for now\n")
            sys.exit()
        else:
            print("Index status                     : User specified")
            fh_run.write("Indexing Time: 0s\n")
            pass


    ### 1. Make Folders ###########################
    ###############################################
    shutil.rmtree("%s" % (res_folder),ignore_errors=True)
    os.mkdir("%s" % (res_folder))

    #### 2. File conversions#######################
    ###############################################

    if libFormat    == "F":
        ### Convert FASTA to Tagcount
        ### Sanity check
        fh_in       = open(libs[0],'r')
        firstline   = fh_in.readline()
        if not firstline.startswith('>') and len(firstline.split('\t')) > 1:
            print("** File doesn't seems to be in FASTA format")
            print("** Please provide correct setting for @libFormat in 'phasis.set' settings file")
            sys.exit()
        else:
            print("#### Converting FASTA format to counts #######")
            dedup_start     = time.time()
            
            ## TEST
            # newList = []
            # for alib in libs:
            #     aname = dedup_process(alib)
            #     newList.append(aname)
            # libs = newList

            libs            = PPResults(dedup_process,libs)
            # print('Converted libs: %s' % (libs))
            dedup_end       = time.time()
            fh_run.write("FASTA conversion time:%ss\n" % (round(dedup_end-dedup_start,2)))
        
    elif libFormat  == "T": 
        ### Can be used as-is, check if it is really 
        ### Sanity check
        fh_in = open(libs[0],'r')
        firstline = fh_in.readline()
        if firstline.startswith('>'):
            print("** File seems tobe in FASTA format")
            print("** Please provide correct setting for @libFormat in 'phasis.set' settings file")
            sys.exit()
        else:
            # print("File seems to be in correct format")
            pass

    else:
        print("** Please provide correct setting for @libFormat in 'phasis.set' settings file")
        print("** If sRNA data is in tag count format use 'T' and for FASTA format use 'F' ")
        sys.exit()


    #### 3. Run Phaser ############################
    ###############################################

    # print('These are the libs: %s' % (libs))
    rawInputs = inputList(libs,runType,genoIndex,deg,nthread,noiseLimit,hitsLimit,clustBuffer)

    # ### Test - Serial Mode
    # for aninput in rawInputs:
    #     PHASBatch2(aninput)

    #### Original - Parallel mode
    PPBalance(PHASBatch2,rawInputs)

    #### close runLog
    phaser_end = time.time()
    fh_run.write("Total analysis time:%ss\n" % (round(phaser_end-phaser_start,2)))
    fh_run.close()

if __name__ == '__main__':

    #### Cores to use for analysis
    nproc = coreReserve(cores)
    ###############
    checkUser()
    checkDependency()
    # checkHost(allowedHost)
    global reference
    libs        = readSet(setFile)
    nthread     = optimize(nproc)
    main(libs)    
    print('\n\n#### Phasing Analysis finished successfully')
    print("#### Results are in folder: %s" % (res_folder))
    print("#### 'phasmerge' can be run by command: python3 phasmerge -mode merge -dir %s\n" % (res_folder))
    sys.exit()

########### CHANGE LOG ########
###############################

### Version 01 -> v02
### Added PARE switch
### Added sRNA ratio option
### Added option to specify libs

## v02 -> v03
## Added option to get libs from the server with hits filter
## COrrected bug in main(), repaced libs with userlibs for specific libraries part
## Perl location added as variable

## v03 -> v04
## Changed order of user settings to make them more clear
## Added functionality to check if the abundance file for library already exists in folder - Saves a lot of time

## v04 -> v05
## Added local mode to run on smallRNA files specified by user and present in current directory unlike fetching from DB or ALLDATA
## Simplfied user settings

## v05 -> v06
## Added extension to sRNA library files for easy copying

## v06 -> v065
## Fixed regresion introduced in v06

## v065 -> v07 [major][stable]
## Includes fix for iltering out tags with no hits, these are inlcuded now for libraries that have no genomes

## v070 -> v075 [major]
## Paralelization schema improved - Now paralelized three libraries together, only the analysis part is parallelized and not downloading part

## v075 -> v080
## Changed nProc input from "Y" to 0
## Fixed bug from v075 if fethLibs = 'Y', then also use libs were being used for raw inputs

## v08 -> v085
## moved scripts to svn/users/kakrana and updated the paths

## v085 -> v090
## Script run on local libraries
## Localization complete
## Added sanity checks
## Index made if change in genome detected, and reused if genome/reference is not changed

## v090 -> v095
## Added the phaster-core production/installed path

## v095 -> v099 [major]
## Added de-duplication functions to handle FASTA file, and convert to required format
## Modified FASTA clean module to implement a relatively faster method (should save a few minutes 2-4 depending on genome)
## Updated runTYPEs - G,T and S modes
## changed genoType to reference in settings reader
## Fixed a buf while checking for previous index - index file was being looked instead of index directory, also added another md5 check to loop
## Added a dependency checks
## Updated script for updated version of phaster core files

## v0.99 - v1.0
## Updated the index builder function with optimized parameters. Now 6-8 minutes faster
## Added a argument to run on low memory

## v1.0 - v1.01
## Remade changes to indexBuilder module by copying the working version from v0.99. Not sure what went wrong in the v1.0

## v1.01 -> v1.02
## Fixed error where comma-seprated @userlibs has a an empty entry, like a stray comma in end. Script doesn't ends in that case 
#### I thought its because of many libraries being used and results not reported back i.e. multiprocessing issue but I was wrong
## Fixed summary file name, it was being written at somewhere else randomly
## nthread parameter comes from optimize function and need not to be defines as a 
#### static global variable

## v1.02 -> v1.03 [major]
## Added IF-loop to catch if index is an *.ebwtl (for big genomes) file before computing its hash
## Added an index integrity checker function to ensure that index file with all six parts exists
## Added a new function "coreReserve" for better assignment of cores for quad, hexa and octacore machines
## "phaser" renamed to "phasdetect"
## Added mindepth, clustbuffer, mismat parameters to phasworks.set for user tunability
## Default setting hardcoded if mindepth, clustbuffer, mismat left empty by users
## Index extension to the indexIntegrity loop when no index is found, else it was giving error at return step

## v1.03 -> v1.04
## Updated phasemerge analysis statement

## v1.04 -> v1.05
## Added sanity checks to readset function

## v1.05 -> v1.06
## Renamed to PHASIS

## v1.06 -> v1.07
## Added check for memory file, if an empty one exists from earlier crash
## Fixed issue with index extension determination for big genomes
## organized the index builder call in main(). It is now called at one place


## TO-DO
## Add automatic index resolution
## Add functionality to share library folder, for 21-,24- and 22nt analysis


## Core-scripts usage
# Mandatory:
#     -i        small RNA input file name
#     -f        two file formats are supported,[t] for tagcount, [f] for fasta.
#     -d        indexed genome by bowtie, indicating the prefix of the genome
#     -px       prefix for each of the file, used to distinguish for eachother
#     -rl       register len(rl), such as 21 or 24, separated by comma: 21,24 etc
# optional:
#     -k        bowtie alignment hits report, default = all
#     -q        degradome or PARE data in ONLY tagcount format: seq   abundance
#     -m        mismatches for both the sRNA and PARE/degradome alignment by bowtie, default = 0
#     -p        p-value in decimal number, defult = 0.005;
#     -cpu      cpu numbers for the bowtie alignment
#     -n        noise, default = 1, for those which have abundance less equal than 1, properly increase
#               noise value for union dataset 
#     -g        gap between two separate cluster, 300bp by default
#     -t        minimal proportation of the interested register small RNA abundance, default = 85
#     -ht       the maximal average of hits for the small RNA of a certain cluster, defaut = 10

